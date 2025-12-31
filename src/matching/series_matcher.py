"""
Series matcher for identifying and grouping audiobooks into series
"""
import logging
import re
from fuzzywuzzy import fuzz
from database.models import AudiobookItem, Series, SeriesMatch
from sqlalchemy import or_
from external.series_lookup import SeriesLookup

logger = logging.getLogger(__name__)

class SeriesMatcher:
    """Matches audiobooks to series using various algorithms"""
    
    def __init__(self, db_session, config_manager, confidence_threshold=70, use_external_lookup=True):
        """Initialize series matcher"""
        self.db_session = db_session
        self.config = config_manager
        self.confidence_threshold = confidence_threshold
        self.use_external_lookup = use_external_lookup
        
        # Initialize external lookup based on config
        self.series_lookup = None
        if use_external_lookup:
            external_config = config_manager.get('external_api', {})
            if external_config.get('enabled'):
                provider = external_config.get('provider', 'openai')
                api_key = external_config.get('openai_api_key') if provider == 'openai' else None
                model = external_config.get('openai_model', 'gpt-4o-mini')
                
                try:
                    self.series_lookup = SeriesLookup(
                        provider=provider,
                        api_key=api_key,
                        model=model
                    )
                    logger.info(f"Initialized external series lookup using {provider}")
                except Exception as e:
                    logger.error(f"Failed to initialize external lookup: {e}")
                    self.series_lookup = None
        
        # Common patterns for series detection
        self.series_patterns = [
            r'(.+?)\s*[,:-]\s*Book\s+(\d+)',
            r'(.+?)\s*[,:-]\s*Vol\.?\s+(\d+)',
            r'(.+?)\s*[,:-]\s*Volume\s+(\d+)',
            r'(.+?)\s*\(Book\s+(\d+)\)',
            r'(.+?)\s*#(\d+)',
            r'(.+?)\s*-\s*(\d+)',
        ]
    
    def extract_series_info(self, title):
        """Extract series name and number from title"""
        if not title:
            return None, None
        
        # Try to match series in parentheses first (e.g., "Title (Series Name, Book 1)")
        parenthetical_patterns = [
            r'\(([^,]+?),?\s*Book\s+(\d+)\)',
            r'\(([^,]+?)\s+Book\s+(\d+)\)',
            r'\(([^,]+?)\s*#(\d+)\)',
            r'\(([^,]+?),?\s*Vol\.?\s+(\d+)\)',
            r'\(([^,]+?),?\s*Volume\s+(\d+)\)',
        ]
        
        for pattern in parenthetical_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                series_name = match.group(1).strip()
                series_index = match.group(2).strip()
                return series_name, series_index
        
        # Then try standard patterns
        for pattern in self.series_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                series_name = match.group(1).strip()
                series_index = match.group(2).strip()
                return series_name, series_index
        
        return None, None
    
    def find_or_create_series(self, series_name, author=None):
        """Find existing series or create new one"""
        # Try to find existing series
        series = self.db_session.query(Series).filter(
            Series.series_name.ilike(f"%{series_name}%")
        ).first()
        
        if series:
            return series
        
        # Create new series
        series = Series(
            series_name=series_name,
            author=author,
            total_books=0
        )
        self.db_session.add(series)
        self.db_session.commit()
        
        logger.info(f"Created new series: {series_name}")
        return series
    
    def match_audiobook_to_series(self, audiobook, series, confidence, method='automatic'):
        """Create a match between audiobook and series"""
        # Check if match already exists
        existing = self.db_session.query(SeriesMatch).filter(
            SeriesMatch.audiobook_id == audiobook.id,
            SeriesMatch.series_id == series.id
        ).first()
        
        if existing:
            existing.confidence_score = confidence
            existing.match_method = method
        else:
            match = SeriesMatch(
                audiobook_id=audiobook.id,
                series_id=series.id,
                confidence_score=confidence,
                match_method=method
            )
            self.db_session.add(match)
        
        self.db_session.commit()
    
    def match_all_audiobooks(self):
        """Attempt to match all audiobooks to series"""
        audiobooks = self.db_session.query(AudiobookItem).all()
        matches_found = 0
        
        for audiobook in audiobooks:
            # Try external lookup first if enabled
            if self.use_external_lookup and self.series_lookup:
                external_result = self.series_lookup.lookup_by_title_author(
                    audiobook.title, 
                    audiobook.author
                )
                
                if external_result and external_result.get('series_name'):
                    series = self.find_or_create_series(
                        external_result['series_name'], 
                        audiobook.author
                    )
                    self.match_audiobook_to_series(audiobook, series, 98, 'external_api')
                    
                    # Use external series_index if available
                    if external_result.get('series_index'):
                        audiobook.series_index = str(external_result['series_index'])
                    else:
                        # Fallback: try to extract series number from title
                        _, series_index = self.extract_series_info(audiobook.title)
                        if series_index:
                            audiobook.series_index = series_index
                            logger.info(f"Extracted series index {series_index} from title for: {audiobook.title}")
                    
                    self.db_session.commit()
                    matches_found += 1
                    continue
            
            # Try series info from metadata first
            if audiobook.series_title:
                series = self.find_or_create_series(
                    audiobook.series_title, 
                    audiobook.author
                )
                self.match_audiobook_to_series(audiobook, series, 95, 'metadata')
                matches_found += 1
                continue
            
            # Try extracting from title
            series_name, series_index = self.extract_series_info(audiobook.title)
            if series_name:
                series = self.find_or_create_series(series_name, audiobook.author)
                self.match_audiobook_to_series(audiobook, series, 85, 'title_pattern')
                
                # Update series index if found
                audiobook.series_index = series_index
                self.db_session.commit()
                matches_found += 1
                continue
            
            # Try fuzzy matching with existing series
            self._fuzzy_match_to_existing_series(audiobook)
        
        logger.info(f"Matched {matches_found} audiobooks to series")
        return matches_found
    
    def _fuzzy_match_to_existing_series(self, audiobook):
        """Attempt fuzzy matching with existing series"""
        all_series = self.db_session.query(Series).all()
        
        best_match = None
        best_score = 0
        
        for series in all_series:
            # Compare with series name
            score = fuzz.partial_ratio(
                audiobook.title.lower(), 
                series.series_name.lower()
            )
            
            # Bonus if authors match
            if audiobook.author and series.author:
                if fuzz.ratio(audiobook.author.lower(), series.author.lower()) > 80:
                    score += 10
            
            if score > best_score and score >= self.confidence_threshold:
                best_score = score
                best_match = series
        
        if best_match:
            self.match_audiobook_to_series(
                audiobook, 
                best_match, 
                best_score, 
                'fuzzy_match'
            )
            
            # Try to extract series index from title
            _, series_index = self.extract_series_info(audiobook.title)
            if series_index:
                audiobook.series_index = series_index
                self.db_session.commit()
                logger.info(f"Extracted series index {series_index} from fuzzy matched title: {audiobook.title}")
    
    def get_unmatched_audiobooks(self):
        """Get audiobooks that haven't been matched to any series"""
        matched_ids = self.db_session.query(SeriesMatch.audiobook_id).distinct()
        unmatched = self.db_session.query(AudiobookItem).filter(
            ~AudiobookItem.id.in_(matched_ids)
        ).all()
        
        return unmatched
    
    def get_pending_matches(self):
        """Get matches that need user approval"""
        return self.db_session.query(SeriesMatch).filter(
            SeriesMatch.user_approved == False,
            SeriesMatch.user_rejected == False
        ).all()

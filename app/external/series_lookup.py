"""
External API client for fetching series information
"""
import logging
import requests
import time
import json
from openai import OpenAI

logger = logging.getLogger(__name__)

class SeriesLookup:
    """Lookup series information from external sources"""
    
    def __init__(self, provider='openai', api_key=None, model='gpt-4o-mini'):
        self.provider = provider
        self.google_books_url = "https://www.googleapis.com/books/v1/volumes"
        self.session = requests.Session()
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 2.0 if provider == 'google_books' else 0.1
        self.rate_limited_until = 0
        
        # OpenAI setup
        self.openai_client = None
        self.openai_model = model
        if provider == 'openai' and api_key:
            try:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info(f"Initialized OpenAI client with model {model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
    def lookup_by_title_author(self, title, author=None):
        """Look up series info using configured provider"""
        if self.provider == 'openai' and self.openai_client:
            return self._lookup_openai(title, author)
        else:
            return self._lookup_google_books(title, author)
    
    def _lookup_openai(self, title, author=None):
        """Look up series info using OpenAI"""
        cache_key = f"openai:{title}:{author}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            author_text = f" by {author}" if author else ""
            prompt = f"""Is the book "{title}"{author_text} part of a series?

If YES:
- What is the exact name of the series?
- What number is this book in the series?

If NO:
- This is a standalone book

Respond ONLY with valid JSON in this exact format:
{{"series_name": "Series Name Here", "series_index": "1"}}

Or if not in a series:
{{"series_name": null, "series_index": null}}

Or if part of a series but NOT a numbered book (e.g., short story collections, graphic novels, companion books):
{{"series_name": "Series Name Here", "series_index": "Companion"}}

Examples:
- "Stormbreaker" by Anthony Horowitz → {{"series_name": "Alex Rider", "series_index": "1"}}
- "Scorpia Rising: Alex Rider, Book 9" → {{"series_name": "Alex Rider", "series_index": "9"}}
- "Alex Rider: Secret Weapon" (short story collection) → {{"series_name": "Alex Rider", "series_index": "Companion"}}
- "One Lost Soul: A Chilling British Detective Crime Thriller (Hidden Norfolk Book 1)" → {{"series_name": "Hidden Norfolk", "series_index": "1"}}
- "The Stand" by Stephen King → {{"series_name": null, "series_index": null}}

IMPORTANT: 
- series_index must be a number as a string (e.g., "1", "2", "10") OR "Companion" for unnumbered companion books
- Use "Companion" for short story collections, graphic novels, or other books in the series universe that aren't part of the main numbered sequence
- Only return the JSON, no other text"""
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert librarian who identifies book series and their reading order. You ALWAYS respond with valid JSON only, never with explanations or other text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                if result.get('series_name'):
                    self.cache[cache_key] = result
                    logger.info(f"Found series via OpenAI: {result}")
                    return result
                else:
                    self.cache[cache_key] = None
                    return None
            except json.JSONDecodeError:
                logger.warning(f"OpenAI returned non-JSON response: {result_text}")
                self.cache[cache_key] = None
                return None
                
        except Exception as e:
            logger.warning(f"OpenAI lookup failed for '{title}': {e}")
            self.cache[cache_key] = None
            return None
    
    def _lookup_google_books(self, title, author=None):
        """Look up series info from Google Books"""
        cache_key = f"{title}:{author}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check if we're currently rate limited
        current_time = time.time()
        if current_time < self.rate_limited_until:
            logger.warning(f"Skipping Google Books lookup - rate limited until {self.rate_limited_until - current_time:.1f}s from now")
            self.cache[cache_key] = None
            return None
        
        # Rate limiting - wait between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        try:
            query = f'intitle:"{title}"'
            if author:
                query += f' inauthor:"{author}"'
            
            self.last_request_time = time.time()
            response = self.session.get(
                self.google_books_url,
                params={
                    'q': query,
                    'maxResults': 1
                },
                timeout=10
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning(f"Google Books rate limit hit - backing off for 60 seconds")
                self.rate_limited_until = time.time() + 60
                self.cache[cache_key] = None
                return None
            
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('totalItems', 0) > 0:
                item = data['items'][0]
                volume_info = item.get('volumeInfo', {})
                
                # Check for series information
                series_info = volume_info.get('seriesInfo')
                if series_info:
                    result = {
                        'series_name': series_info.get('volumeSeries', [{}])[0].get('seriesId'),
                        'series_index': series_info.get('bookDisplayNumber')
                    }
                    self.cache[cache_key] = result
                    logger.info(f"Found series via Google Books: {result}")
                    return result
                
                # Alternative: check categories or description
                categories = volume_info.get('categories', [])
                for category in categories:
                    if 'book' in category.lower() and any(char.isdigit() for char in category):
                        # Might contain series info
                        logger.info(f"Potential series in category: {category}")
            
            self.cache[cache_key] = None
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Google Books rate limit hit - backing off for 60 seconds")
                self.rate_limited_until = time.time() + 60
            else:
                logger.warning(f"Google Books lookup failed for '{title}': {e}")
            self.cache[cache_key] = None
            return None
        except Exception as e:
            logger.warning(f"Google Books lookup failed for '{title}': {e}")
            self.cache[cache_key] = None
            return None
    
    def lookup_openlibrary(self, title, author=None):
        """Look up series info from Open Library"""
        try:
            query = title
            if author:
                query += f" {author}"
            
            response = self.session.get(
                "https://openlibrary.org/search.json",
                params={
                    'q': query,
                    'limit': 1
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('docs'):
                doc = data['docs'][0]
                
                # Check for series
                if 'id_goodreads' in doc or 'id_amazon' in doc:
                    # Has external IDs, might have series info
                    logger.info(f"Found potential series info in Open Library")
                
                # Some books have series in title or subjects
                subjects = doc.get('subject', [])
                for subject in subjects:
                    if 'series' in subject.lower():
                        logger.info(f"Series mention in subjects: {subject}")
            
            time.sleep(0.5)  # Rate limiting
            return None
            
        except Exception as e:
            logger.warning(f"Open Library lookup failed for '{title}': {e}")
            return None

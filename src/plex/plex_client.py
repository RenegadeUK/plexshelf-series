"""
Plex API client for interacting with Plex Media Server
"""
import logging
import requests
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class PlexClient:
    """Client for interacting with Plex API"""
    
    def __init__(self, base_url=None, token=None):
        """Initialize Plex client"""
        self.base_url = base_url.rstrip('/') if base_url else None
        self.token = token
        self.session = requests.Session()
        self.library_key = None
        self.server_name = None
        
    def connect(self, base_url=None, token=None):
        """Connect to Plex server"""
        if base_url:
            self.base_url = base_url.rstrip('/')
        if token:
            self.token = token
            
        if not self.base_url or not self.token:
            raise ValueError("Plex URL and token are required")
        
        try:
            # Test connection and get server info
            response = self.session.get(
                f"{self.base_url}/",
                headers={"X-Plex-Token": self.token},
                timeout=10
            )
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            self.server_name = root.get('friendlyName', 'Unknown')
            
            logger.info(f"Connected to Plex server: {self.server_name}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Invalid Plex token")
                raise ValueError("Invalid Plex token")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Plex: {e}", exc_info=True)
            raise
    
    def get_library(self, library_name="Audiobooks"):
        """Get Plex library by name"""
        if not self.base_url or not self.token:
            raise RuntimeError("Not connected to Plex server")
        
        try:
            response = self.session.get(
                f"{self.base_url}/library/sections",
                headers={"X-Plex-Token": self.token},
                timeout=10
            )
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            for directory in root.findall('.//Directory'):
                if directory.get('title') == library_name:
                    self.library_key = directory.get('key')
                    logger.info(f"Found library: {library_name} (key: {self.library_key})")
                    return self.library_key
            
            raise ValueError(f"Library '{library_name}' not found")
            
        except Exception as e:
            logger.error(f"Failed to get library: {e}", exc_info=True)
            raise
    
    def get_all_audiobooks(self):
        """Get all audiobooks from the library"""
        if not self.library_key:
            raise RuntimeError("Library not loaded")
        
        try:
            # Try to get albums directly first
            response = self.session.get(
                f"{self.base_url}/library/sections/{self.library_key}/all",
                headers={"X-Plex-Token": self.token},
                params={"type": 9},  # Type 9 = albums
                timeout=30
            )
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            audiobooks = []
            
            for elem in root.findall('.//Directory'):
                if elem.get('type') == 'album':
                    audiobooks.append(elem)
            
            logger.info(f"Direct album fetch found {len(audiobooks)} albums")
            
            # If no albums found, fetch via artists
            if len(audiobooks) == 0:
                logger.info("Fetching audiobooks via artists...")
                
                # Get all artists
                artists_response = self.session.get(
                    f"{self.base_url}/library/sections/{self.library_key}/all",
                    headers={"X-Plex-Token": self.token},
                    params={"type": 8},  # Type 8 = artists
                    timeout=30
                )
                artists_response.raise_for_status()
                artists_root = ET.fromstring(artists_response.content)
                
                artists = artists_root.findall('.//Directory')
                logger.info(f"Found {len(artists)} artists, fetching their albums...")
                
                # For each artist, get their albums
                for artist in artists:
                    artist_key = artist.get('key')
                    artist_title = artist.get('title', 'Unknown')
                    
                    if artist_key:
                        try:
                            albums_response = self.session.get(
                                f"{self.base_url}{artist_key}",
                                headers={"X-Plex-Token": self.token},
                                timeout=30
                            )
                            albums_response.raise_for_status()
                            albums_root = ET.fromstring(albums_response.content)
                            
                            artist_albums = albums_root.findall('.//Directory[@type="album"]')
                            logger.info(f"Artist '{artist_title}' has {len(artist_albums)} albums")
                            audiobooks.extend(artist_albums)
                        except Exception as e:
                            logger.warning(f"Failed to fetch albums for {artist_title}: {e}")
            
            logger.info(f"Total audiobooks found: {len(audiobooks)}")
            return audiobooks
            
        except Exception as e:
            logger.error(f"Failed to fetch audiobooks: {e}", exc_info=True)
            raise
    
    def get_audiobook_metadata(self, audiobook_elem):
        """Extract metadata from audiobook XML element"""
        metadata = {
            'plex_id': audiobook_elem.get('ratingKey'),
            'title': audiobook_elem.get('title'),
            'author': audiobook_elem.get('parentTitle') or audiobook_elem.get('originalTitle'),
            'series_title': None,
            'series_index': None,
            'year': int(audiobook_elem.get('year', 0)) if audiobook_elem.get('year') else None,
            'duration': int(audiobook_elem.get('duration', 0)) // 1000,  # Convert to seconds
            'file_path': None
        }
        
        # Try to get series info from collections
        for collection in audiobook_elem.findall('.//Collection'):
            tag = collection.get('tag', '')
            if 'series' in tag.lower():
                metadata['series_title'] = tag
                break
        
        # Get file path from media
        media = audiobook_elem.find('.//Media/Part')
        if media is not None:
            metadata['file_path'] = media.get('file')
        
        return metadata
    
    def create_collection(self, collection_name, audiobook_ids):
        """Create or update a collection in Plex"""
        if not self.library_key:
            raise RuntimeError("Library not loaded")
        
        try:
            # Add each audiobook to the collection
            for book_id in audiobook_ids:
                response = self.session.put(
                    f"{self.base_url}/library/sections/{self.library_key}/all",
                    params={
                        "type": 9,  # Collection type
                        "id": book_id,
                        "collection[0].tag.tag": collection_name
                    },
                    headers={"X-Plex-Token": self.token},
                    timeout=10
                )
                response.raise_for_status()
            
            logger.info(f"Created/updated collection '{collection_name}' with {len(audiobook_ids)} items")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}", exc_info=True)
            raise
    
    def update_sort_title(self, audiobook_id, series_name, series_index):
        """Update the titleSort field for an audiobook to ensure proper series ordering"""
        if not self.library_key:
            raise RuntimeError("Library not loaded")
        
        try:
            # Format series_index with padding (number first for proper sorting)
            if series_index and series_index.lower() != 'companion':
                try:
                    index_num = int(float(series_index))
                    sort_prefix = f"{index_num:02d} - {series_name}"
                except (ValueError, TypeError):
                    sort_prefix = f"99 - {series_name}"  # Unknown numbers at end
            elif series_index and series_index.lower() == 'companion':
                sort_prefix = f"99 - {series_name} Companion"  # Companions at end
            else:
                sort_prefix = f"99 - {series_name}"  # No index at end
            
            # Update the titleSort field
            response = self.session.put(
                f"{self.base_url}/library/metadata/{audiobook_id}",
                params={
                    "type": 9,
                    "id": audiobook_id,
                    "titleSort.value": sort_prefix,
                    "titleSort.locked": 1
                },
                headers={"X-Plex-Token": self.token},
                timeout=10
            )
            response.raise_for_status()
            
            logger.debug(f"Updated sort title for {audiobook_id} to '{sort_prefix}'")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to update sort title for {audiobook_id}: {e}")
            return False
    
    def test_connection(self):
        """Test connection to Plex server"""
        try:
            if self.base_url and self.token:
                response = self.session.get(
                    f"{self.base_url}/",
                    headers={"X-Plex-Token": self.token},
                    timeout=5
                )
                return response.status_code == 200
            return False
        except:
            return False

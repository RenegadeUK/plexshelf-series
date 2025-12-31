"""
Configuration management for PlexShelf Series Manager
"""
import os
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_dir="/config"):
        """Initialize configuration manager"""
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.yaml"
        self.config = self._load_default_config()
        
    def _load_default_config(self):
        """Load default configuration"""
        return {
            'plex': {
                'url': '',
                'token': '',
                'library_name': 'Audiobooks',
                'timeout': 30
            },
            'matching': {
                'confidence_threshold': 70,
                'auto_approve_threshold': 95,
                'fuzzy_match_enabled': True
            },
            'external_api': {
                'provider': 'openai',  # 'openai' or 'google_books'
                'openai_api_key': '',
                'openai_model': 'gpt-4o-mini',
                'enabled': False
            },
            'ui': {
                'theme': 'default',
                'window_size': '1024x768',
                'auto_refresh': False
            },
            'logging': {
                'level': 'INFO',
                'file': '/config/plexshelf.log'
            }
        }
    
    def load(self):
        """Load configuration from file"""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = yaml.safe_load(f) or {}
                    # Merge with defaults
                    self._merge_config(self.config, loaded_config)
                logger.info("Configuration loaded successfully")
            else:
                logger.info("No existing config found, using defaults")
                self.save()  # Save default config
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}", exc_info=True)
        
        return self.config
    
    def save(self):
        """Save current configuration to file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            
            logger.info("Configuration saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}", exc_info=True)
            return False
    
    def _merge_config(self, base, update):
        """Recursively merge configuration dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path, default=None):
        """Get configuration value by dot-notation path"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path, value):
        """Set configuration value by dot-notation path"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def update_plex_config(self, url, token, library_name=None):
        """Update Plex connection configuration"""
        self.config['plex']['url'] = url
        self.config['plex']['token'] = token
        if library_name:
            self.config['plex']['library_name'] = library_name
        return self.save()

"""
PlexShelf Series Manager
Main entry point for the web application
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import logging
from src.web_app import app
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger()

def main():
    """Main application entry point"""
    try:
        logger.info("Starting PlexShelf Series Manager Web Server")
        logger.info("Access the UI at http://localhost:8080")
        
        # Start the Flask web application
        app.run(host='0.0.0.0', port=8080, debug=False)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

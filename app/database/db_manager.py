"""
Database manager for handling all database operations
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self, db_path="/data/plexshelf.db"):
        """Initialize database manager"""
        self.db_path = db_path
        self.engine = None
        self.Session = None
        
    def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create engine
            self.engine = create_engine(
                f'sqlite:///{self.db_path}',
                echo=False,
                pool_pre_ping=True
            )
            
            # Create session factory
            session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(session_factory)
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            logger.info(f"Database initialized at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            return False
    
    def get_session(self):
        """Get a new database session"""
        if self.Session is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.Session()
    
    def close(self):
        """Close database connections"""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")

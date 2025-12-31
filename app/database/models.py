"""
Database models for PlexShelf Series Manager
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class AudiobookItem(Base):
    """Model for individual audiobook items from Plex"""
    __tablename__ = 'audiobook_items'
    
    id = Column(Integer, primary_key=True)
    plex_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    author = Column(String(500))
    series_title = Column(String(500))
    series_index = Column(String(50))
    year = Column(Integer)
    duration = Column(Integer)  # in seconds
    file_path = Column(Text)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to matched series
    series_matches = relationship("SeriesMatch", back_populates="audiobook")
    
    def __repr__(self):
        return f"<AudiobookItem(title='{self.title}', author='{self.author}')>"


class Series(Base):
    """Model for audiobook series"""
    __tablename__ = 'series'
    
    id = Column(Integer, primary_key=True)
    series_name = Column(String(500), nullable=False)
    author = Column(String(500))
    total_books = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to matches
    matches = relationship("SeriesMatch", back_populates="series")
    
    def __repr__(self):
        return f"<Series(name='{self.series_name}', books={self.total_books})>"


class SeriesMatch(Base):
    """Model for matching audiobooks to series"""
    __tablename__ = 'series_matches'
    
    id = Column(Integer, primary_key=True)
    audiobook_id = Column(Integer, ForeignKey('audiobook_items.id'), nullable=False)
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)
    confidence_score = Column(Integer, default=0)  # 0-100
    match_method = Column(String(50))  # 'automatic', 'manual', 'override'
    user_approved = Column(Boolean, default=False)
    user_rejected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    # Relationships
    audiobook = relationship("AudiobookItem", back_populates="series_matches")
    series = relationship("Series", back_populates="matches")
    
    def __repr__(self):
        return f"<SeriesMatch(audiobook_id={self.audiobook_id}, series_id={self.series_id}, score={self.confidence_score})>"


class PlexCollection(Base):
    """Model for Plex collections to be created/updated"""
    __tablename__ = 'plex_collections'
    
    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)
    collection_name = Column(String(500), nullable=False)
    plex_collection_id = Column(String(100))  # ID in Plex once created
    status = Column(String(50), default='pending')  # pending, created, updated, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    synced_at = Column(DateTime)
    
    def __repr__(self):
        return f"<PlexCollection(name='{self.collection_name}', status='{self.status}')>"

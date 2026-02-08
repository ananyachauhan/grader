"""
Database models for BUSN 403 Grading Platform
"""
# IMPORTANT: Import pysqlite3 BEFORE any SQLAlchemy imports
# This ensures it's available when SQLAlchemy tries to load the dialect
import sys
try:
    import pysqlite3
    # Replace sqlite3 module with pysqlite3 for compatibility
    sys.modules['sqlite3'] = pysqlite3
    # Also make pysqlite3 directly available for SQLAlchemy dialect
    sys.modules['pysqlite3'] = pysqlite3
except ImportError:
    # Fall back to built-in sqlite3 for local development
    pass

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Section(Base):
    __tablename__ = 'sections'
    
    id = Column(Integer, primary_key=True)
    section_number = Column(String(10), unique=True, nullable=False)  # '900', '901', '902'
    course_code = Column(String(20), default='BUSN 403')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    assignments = relationship("Assignment", back_populates="section", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # 'professor' or 'ta'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    created_assignments = relationship("Assignment", foreign_keys="Assignment.created_by", back_populates="creator")
    grading_sessions = relationship("GradingSession", foreign_keys="GradingSession.graded_by", back_populates="grader")
    reviewed_sessions = relationship("GradingSession", foreign_keys="GradingSession.reviewed_by", back_populates="reviewer")

class Assignment(Base):
    __tablename__ = 'assignments'
    
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    rubric_filename = Column(String(200), nullable=False)
    custom_instructions = Column(Text)
    drive_folder_id = Column(String(200), nullable=False)
    status = Column(String(20), default='draft')  # 'draft', 'active', 'completed'
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    section = relationship("Section", back_populates="assignments")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_assignments")
    grading_sessions = relationship("GradingSession", back_populates="assignment")
    documents = relationship("AssignmentDocument", back_populates="assignment", cascade="all, delete-orphan")

class GradingSession(Base):
    __tablename__ = 'grading_sessions'
    
    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey('assignments.id'), nullable=False)
    graded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    doc_ids = Column(Text, nullable=False)  # JSON array
    results = Column(Text, nullable=False)  # JSON results
    status = Column(String(20), default='pending_review')  # 'pending_review', 'approved', 'rejected'
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    assignment = relationship("Assignment", back_populates="grading_sessions")
    grader = relationship("User", foreign_keys=[graded_by], back_populates="grading_sessions")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="reviewed_sessions")

class AssignmentDocument(Base):
    __tablename__ = 'assignment_documents'
    
    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey('assignments.id'), nullable=False)
    doc_id = Column(String(200), nullable=False)
    doc_name = Column(String(300), nullable=False)
    status = Column(String(20), default='ungraded')  # 'ungraded', 'graded', 'reviewed'
    graded_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    
    assignment = relationship("Assignment", back_populates="documents")

# Database engine (singleton)
_db_engine = None
_db_session_factory = None

def get_db_engine():
    """Get or create database engine"""
    global _db_engine
    if _db_engine is None:
        from pathlib import Path
        import os
        
        # Check for Fly.io persistent volume path
        fly_volume_path = os.getenv('FLY_VOLUME_PATH', '/data')
        db_path = Path(fly_volume_path) / 'busn403_grading.db'
        
        # Fallback to local path for development
        if not db_path.parent.exists():
            db_path = Path(__file__).parent / 'busn403_grading.db'
        
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use sqlite:// with sys.modules replacement
        # The sys.modules['sqlite3'] = pysqlite3 replacement at the top
        # ensures SQLAlchemy uses pysqlite3 even with sqlite:// URL
        db_url = f'sqlite:///{db_path}'
        
        _db_engine = create_engine(
            db_url,
            echo=False,
            connect_args={'check_same_thread': False}
        )
    return _db_engine

def get_db_session():
    """Get database session"""
    global _db_session_factory
    if _db_session_factory is None:
        engine = get_db_engine()
        _db_session_factory = sessionmaker(bind=engine)
    return _db_session_factory()

# Database setup
def init_db():
    """Initialize database with tables and default data"""
    engine = get_db_engine()
    Base.metadata.create_all(engine)
    
    session = get_db_session()
    
    try:
        # Create default sections if they don't exist
        sections = ['900', '901', '902']
        for section_num in sections:
            existing = session.query(Section).filter_by(section_number=section_num).first()
            if not existing:
                session.add(Section(section_number=section_num))
        
        # Create default admin user if needed
        admin = session.query(User).filter_by(email='admin@busn403.edu').first()
        if not admin:
            session.add(User(
                email='admin@busn403.edu',
                name='Admin User',
                role='professor'
            ))
        
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
    
    return engine


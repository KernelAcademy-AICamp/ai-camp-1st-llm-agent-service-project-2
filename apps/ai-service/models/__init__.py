"""
AI Service Models
SQLAlchemy models for PostgreSQL access
- Read-only: get_db (기본)
- Read-Write: get_write_db (크롤러용)
"""

from .database import Base, get_db, get_write_db, init_db, close_db, engine, write_engine
from .precedent_feedback import PrecedentFeedbackStats
from .precedent import Precedent

__all__ = [
    'Base',
    'get_db',
    'get_write_db',
    'init_db',
    'close_db',
    'engine',
    'write_engine',
    'PrecedentFeedbackStats',
    'Precedent',
]

"""
Database module for legal document storage.
Provides PostgreSQL integration for structured legal data.
"""

from .postgres_client import PostgreSQLClient
from .schema import create_all_tables, drop_all_tables

__all__ = ['PostgreSQLClient', 'create_all_tables', 'drop_all_tables']

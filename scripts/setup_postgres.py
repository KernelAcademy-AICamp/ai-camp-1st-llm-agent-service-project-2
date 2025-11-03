#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script
교통법 데이터베이스 초기화 스크립트

Usage:
    python scripts/setup_postgres.py --init        # Create tables
    python scripts/setup_postgres.py --drop        # Drop all tables
    python scripts/setup_postgres.py --test        # Test connection
    python scripts/setup_postgres.py --stats       # Show statistics
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import PostgreSQLClient, create_all_tables, drop_all_tables
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_config():
    """Get database configuration from environment variables."""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DATABASE', 'criminal_law_db'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', '')
    }


def init_database():
    """Initialize database with all tables."""
    print("\n" + "="*60)
    print("🔨 Initializing PostgreSQL Database")
    print("="*60 + "\n")

    config = get_db_config()
    print(f"Host: {config['host']}:{config['port']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}\n")

    try:
        client = PostgreSQLClient(config)
        create_all_tables(client.connection)
        client.close()
        print("\n✅ Database initialized successfully!\n")
    except Exception as e:
        print(f"\n❌ Failed to initialize database: {e}\n")
        sys.exit(1)


def drop_database():
    """Drop all tables from database."""
    print("\n" + "="*60)
    print("🗑️  Dropping All Tables")
    print("="*60 + "\n")

    response = input("⚠️  This will delete all data. Are you sure? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return

    config = get_db_config()

    try:
        client = PostgreSQLClient(config)
        drop_all_tables(client.connection)
        client.close()
        print("\n✅ All tables dropped successfully!\n")
    except Exception as e:
        print(f"\n❌ Failed to drop tables: {e}\n")
        sys.exit(1)


def test_connection():
    """Test database connection."""
    print("\n" + "="*60)
    print("🔌 Testing Database Connection")
    print("="*60 + "\n")

    config = get_db_config()
    print(f"Host: {config['host']}:{config['port']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}\n")

    try:
        client = PostgreSQLClient(config)
        print("✅ Connection successful!")

        # Test query
        cursor = client.connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()

        print(f"PostgreSQL version: {version[:50]}...\n")

        client.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}\n")
        sys.exit(1)


def show_stats():
    """Show database statistics."""
    print("\n" + "="*60)
    print("📊 Database Statistics")
    print("="*60 + "\n")

    config = get_db_config()

    try:
        client = PostgreSQLClient(config)
        stats = client.get_stats()

        print("Table Statistics:")
        print("-" * 40)
        for table, count in stats.items():
            print(f"  {table:<25} {count:>10,}")
        print("-" * 40)
        print(f"  {'Total':<25} {sum(stats.values()):>10,}\n")

        client.close()
    except Exception as e:
        print(f"❌ Failed to get statistics: {e}\n")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='PostgreSQL Database Setup')
    parser.add_argument('--init', action='store_true', help='Initialize database tables')
    parser.add_argument('--drop', action='store_true', help='Drop all tables')
    parser.add_argument('--test', action='store_true', help='Test database connection')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')

    args = parser.parse_args()

    if args.init:
        init_database()
    elif args.drop:
        drop_database()
    elif args.test:
        test_connection()
    elif args.stats:
        show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

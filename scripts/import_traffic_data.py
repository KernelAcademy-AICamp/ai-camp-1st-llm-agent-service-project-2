#!/usr/bin/env python3
"""
Traffic Law Data Import Pipeline
교통법 데이터 전체 임포트 파이프라인
- CSV 파싱 → PostgreSQL 저장 → 통계 출력
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import PostgreSQLClient, create_all_tables, drop_all_tables
from core.preprocessing import LawParser, PrecedentParser, TrafficMetadataExtractor
from scripts.traffic_law_data_loader import TrafficLawDataLoader


def init_database(drop_existing: bool = False):
    """
    Initialize PostgreSQL database.

    Args:
        drop_existing: Drop existing tables before creating new ones
    """
    print("\n" + "="*60)
    print("🗄️  PostgreSQL Database Initialization")
    print("="*60 + "\n")

    try:
        db_client = PostgreSQLClient()

        if drop_existing:
            print("⚠️  Dropping existing tables...")
            drop_all_tables(db_client.conn)
            print("✅ Tables dropped\n")

        print("📋 Creating tables...")
        create_all_tables(db_client.conn)
        print("✅ Tables created successfully\n")

        db_client.close()

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def import_laws_to_db(base_path: str = None, max_files: int = None):
    """
    Import law CSV files to PostgreSQL.

    Args:
        base_path: Base path to data directory
        max_files: Maximum number of files to import
    """
    print("\n" + "="*60)
    print("📚 Importing Laws to PostgreSQL")
    print("="*60 + "\n")

    try:
        db_client = PostgreSQLClient()
        parser = LawParser()
        traffic_extractor = TrafficMetadataExtractor()

        # 법령 CSV 파일 경로
        if base_path:
            source_path = Path(base_path) / "Training/01.원천데이터/TS_법령"
        else:
            source_path = Path("04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터/Training/01.원천데이터/TS_법령")

        if not source_path.exists():
            print(f"❌ Source path not found: {source_path}")
            return

        csv_files = list(source_path.glob("*.csv"))
        print(f"Found {len(csv_files)} CSV files\n")

        if max_files:
            csv_files = csv_files[:max_files]
            print(f"Processing first {max_files} files...\n")

        imported_count = 0
        traffic_count = 0

        for csv_file in csv_files:
            try:
                # Parse CSV
                law_data = parser.parse_csv(csv_file)

                # Extract traffic metadata
                full_text = "\n".join(art.get('content', '') for art in law_data['articles'])
                traffic_meta = traffic_extractor.extract(full_text)

                # Insert law
                law_id = db_client.insert_law(
                    law_id=law_data['law_id'],
                    law_title=law_data['law_title'],
                    law_num=law_data.get('law_num'),
                    promulgation_date=law_data.get('promulgation_date'),
                    enforcement_date=law_data.get('enforcement_date'),
                    category=law_data.get('category'),
                    is_traffic_related=traffic_meta['is_traffic_related']
                )

                # Insert articles
                db_client.insert_law_articles(law_data['articles'])

                imported_count += 1
                if traffic_meta['is_traffic_related']:
                    traffic_count += 1
                    print(f"✅ [{imported_count}/{len(csv_files)}] {law_data['law_title']} (교통법 관련)")
                else:
                    print(f"✅ [{imported_count}/{len(csv_files)}] {law_data['law_title']}")

            except Exception as e:
                print(f"⚠️  Failed to import {csv_file.name}: {e}")
                continue

        print(f"\n✅ Import completed!")
        print(f"   Total imported: {imported_count} laws")
        print(f"   Traffic-related: {traffic_count} laws\n")

        db_client.close()

    except Exception as e:
        print(f"❌ Law import failed: {e}")
        import traceback
        traceback.print_exc()


def import_precedents_to_db(base_path: str = None, max_files: int = None):
    """
    Import precedent CSV files to PostgreSQL.

    Args:
        base_path: Base path to data directory
        max_files: Maximum number of files to import
    """
    print("\n" + "="*60)
    print("⚖️  Importing Precedents to PostgreSQL")
    print("="*60 + "\n")

    try:
        db_client = PostgreSQLClient()
        parser = PrecedentParser()
        traffic_extractor = TrafficMetadataExtractor()

        # 판결문 CSV 파일 경로
        if base_path:
            source_path = Path(base_path) / "Training/01.원천데이터/TS_판결문"
        else:
            source_path = Path("04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터/Training/01.원천데이터/TS_판결문")

        if not source_path.exists():
            print(f"❌ Source path not found: {source_path}")
            return

        csv_files = list(source_path.glob("*.csv"))
        print(f"Found {len(csv_files)} CSV files\n")

        if max_files:
            csv_files = csv_files[:max_files]
            print(f"Processing first {max_files} files...\n")

        imported_count = 0
        traffic_count = 0

        for csv_file in csv_files:
            try:
                # Parse CSV
                precedent_data = parser.parse_csv(csv_file)

                # Extract traffic metadata from full content
                full_text = " ".join([
                    precedent_data.get('summary', ''),
                    precedent_data.get('judgment', ''),
                    precedent_data.get('reasoning', '')
                ])
                traffic_meta = traffic_extractor.extract(full_text)

                # Insert precedent
                precedent_id = db_client.insert_precedent(
                    precedent_id=precedent_data['precedent_id'],
                    case_num=precedent_data['case_num'],
                    court_name=precedent_data['court_name'],
                    sentence_date=precedent_data.get('sentence_date'),
                    case_name=precedent_data.get('case_name'),
                    case_type=precedent_data.get('case_type'),
                    judgment_type=precedent_data.get('judgment_type'),
                    is_traffic_related=traffic_meta['is_traffic_related']
                )

                # Insert sections
                sections = parser.create_sections_list(precedent_data)
                db_client.insert_precedent_sections(sections)

                # Insert traffic case info if traffic-related
                if traffic_meta['is_traffic_related']:
                    traffic_count += 1
                    # Extract penalty details for traffic case
                    for penalty_type, penalty_value in traffic_meta['penalty_details'].items():
                        db_client.insert_traffic_case(
                            precedent_id=precedent_data['precedent_id'],
                            violation_type=traffic_meta['violation_types'][0] if traffic_meta['violation_types'] else None,
                            blood_alcohol=traffic_meta['blood_alcohol'],
                            sentence_type=penalty_type,
                            sentence_detail=penalty_value,
                            traffic_law_article=traffic_meta['related_laws'][0] if traffic_meta['related_laws'] else None
                        )
                    print(f"✅ [{imported_count+1}/{len(csv_files)}] {precedent_data['case_num']} (교통법 관련)")
                else:
                    print(f"✅ [{imported_count+1}/{len(csv_files)}] {precedent_data['case_num']}")

                imported_count += 1

            except Exception as e:
                print(f"⚠️  Failed to import {csv_file.name}: {e}")
                continue

        print(f"\n✅ Import completed!")
        print(f"   Total imported: {imported_count} precedents")
        print(f"   Traffic-related: {traffic_count} precedents\n")

        db_client.close()

    except Exception as e:
        print(f"❌ Precedent import failed: {e}")
        import traceback
        traceback.print_exc()


def show_statistics():
    """Show database statistics."""
    print("\n" + "="*60)
    print("📊 Database Statistics")
    print("="*60 + "\n")

    try:
        db_client = PostgreSQLClient()

        stats = db_client.get_traffic_statistics()

        print("Overall Statistics:")
        print(f"  Laws: {stats['total_laws']}")
        print(f"  Law Articles: {stats['total_law_articles']}")
        print(f"  Precedents: {stats['total_precedents']}")
        print(f"  Precedent Sections: {stats['total_precedent_sections']}")
        print(f"\nTraffic-Related:")
        print(f"  Laws: {stats['traffic_laws']}")
        print(f"  Precedents: {stats['traffic_precedents']}")
        print(f"  Traffic Cases: {stats['traffic_cases']}\n")

        db_client.close()

    except Exception as e:
        print(f"❌ Failed to get statistics: {e}")


def test_traffic_loader():
    """Test traffic law data loader."""
    print("\n" + "="*60)
    print("🧪 Testing Traffic Law Data Loader")
    print("="*60 + "\n")

    try:
        loader = TrafficLawDataLoader()

        # Test 1: Load traffic-only data
        print("Test 1: Loading traffic-only documents (max 10 per type)...")
        traffic_docs = loader.load_traffic_only(
            use_source=True,
            use_labeled=True,
            max_per_type=10,
            split='training'
        )

        print(f"\n✅ Loaded {len(traffic_docs)} traffic documents")

        # Test 2: Get statistics
        print("\nTest 2: Getting traffic statistics...")
        stats = loader.get_traffic_stats_summary(traffic_docs)

        print(f"\nTraffic Statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Violation types: {len(stats['violation_types'])}")
        print(f"  Accident types: {len(stats['accident_types'])}")
        print(f"  Penalties: {len(stats['penalties'])}")

        if stats['blood_alcohol_range']['count'] > 0:
            print(f"\n  Blood Alcohol Range:")
            print(f"    Min: {stats['blood_alcohol_range']['min']:.3f}%")
            print(f"    Max: {stats['blood_alcohol_range']['max']:.3f}%")
            print(f"    Avg: {stats['blood_alcohol_range']['avg']:.3f}%")
            print(f"    Count: {stats['blood_alcohol_range']['count']}")

        print("\n✅ Tests completed successfully\n")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Traffic Law Data Import Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize database (drop existing tables)
  python scripts/import_traffic_data.py --init-db --drop

  # Import laws (first 10 files)
  python scripts/import_traffic_data.py --import-laws --max-files 10

  # Import precedents (first 10 files)
  python scripts/import_traffic_data.py --import-precedents --max-files 10

  # Show statistics
  python scripts/import_traffic_data.py --stats

  # Test loader
  python scripts/import_traffic_data.py --test

  # Complete pipeline (init + import + stats)
  python scripts/import_traffic_data.py --init-db --drop \\
                                         --import-laws --max-files 10 \\
                                         --import-precedents --max-files 10 \\
                                         --stats
"""
    )

    parser.add_argument('--init-db', action='store_true',
                        help='Initialize PostgreSQL database')
    parser.add_argument('--drop', action='store_true',
                        help='Drop existing tables before creating new ones')
    parser.add_argument('--import-laws', action='store_true',
                        help='Import law CSV files to database')
    parser.add_argument('--import-precedents', action='store_true',
                        help='Import precedent CSV files to database')
    parser.add_argument('--stats', action='store_true',
                        help='Show database statistics')
    parser.add_argument('--test', action='store_true',
                        help='Test traffic law data loader')
    parser.add_argument('--max-files', type=int,
                        help='Maximum number of files to import per type')
    parser.add_argument('--base-path', type=str,
                        help='Base path to data directory')

    args = parser.parse_args()

    # If no arguments, show help
    if not any([args.init_db, args.import_laws, args.import_precedents,
                args.stats, args.test]):
        parser.print_help()
        return

    # Execute requested operations
    if args.init_db:
        success = init_database(drop_existing=args.drop)
        if not success:
            print("❌ Database initialization failed. Aborting.")
            return

    if args.import_laws:
        import_laws_to_db(base_path=args.base_path, max_files=args.max_files)

    if args.import_precedents:
        import_precedents_to_db(base_path=args.base_path, max_files=args.max_files)

    if args.stats:
        show_statistics()

    if args.test:
        test_traffic_loader()

    print("✅ All operations completed!\n")


if __name__ == "__main__":
    main()

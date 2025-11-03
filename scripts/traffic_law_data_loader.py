"""
Traffic Law Data Loader
교통법 데이터 특화 로더 - CriminalLawDataLoader 상속
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.criminal_law_data_loader import CriminalLawDataLoader
from core.preprocessing import TrafficMetadataExtractor
from core.database import PostgreSQLClient
from typing import List, Dict, Any, Optional


class TrafficLawDataLoader(CriminalLawDataLoader):
    """
    교통법 데이터 전용 로더
    - CriminalLawDataLoader의 기본 기능 상속
    - 교통법 필터링 기능 추가
    - PostgreSQL 연동 지원
    - 메타데이터 자동 추출
    """

    def __init__(self, base_path: str = None):
        """
        Initialize traffic law data loader.

        Args:
            base_path: Base path to data directory
        """
        super().__init__(base_path)
        self.traffic_extractor = TrafficMetadataExtractor()
        self.db_client = None

    def set_db_client(self, db_client: PostgreSQLClient):
        """
        Set PostgreSQL client for context enrichment.

        Args:
            db_client: PostgreSQL client instance
        """
        self.db_client = db_client

    def load_traffic_only(
        self,
        use_source: bool = True,
        use_labeled: bool = True,
        source_types: List[str] = None,
        labeled_types: List[str] = None,
        max_per_type: int = None,
        split: str = 'training'
    ) -> List[Dict[str, Any]]:
        """
        Load only traffic-related documents.

        Args:
            use_source: Use source data
            use_labeled: Use labeled data
            source_types: Source data types
            labeled_types: Labeled data types
            max_per_type: Max documents per type
            split: Data split ('training', 'validation', 'all')

        Returns:
            List of traffic-related documents
        """
        print("\n" + "="*60)
        print("🚗 교통법 데이터 로딩 (필터링 모드)")
        print("="*60 + "\n")

        # 기본 로더로 전체 데이터 로드
        all_docs = self.load_dataset(
            use_source=use_source,
            use_labeled=use_labeled,
            source_types=source_types,
            labeled_types=labeled_types,
            max_per_type=max_per_type,
            split=split
        )

        print(f"\n🔍 교통법 관련 문서 필터링 중...")
        print(f"  전체 문서: {len(all_docs)}개")

        # 교통법 관련 문서만 필터링
        traffic_docs = []

        for doc in all_docs:
            content = doc.get('content', '')

            # 교통법 메타데이터 추출
            traffic_meta = self.traffic_extractor.extract(content)

            if traffic_meta['is_traffic_related']:
                # 기존 메타데이터에 교통법 메타데이터 추가
                if 'metadata' not in doc:
                    doc['metadata'] = {}

                doc['metadata'].update({
                    'traffic_related': True,
                    'violation_types': traffic_meta['violation_types'],
                    'accident_types': traffic_meta['accident_types'],
                    'penalties': traffic_meta['penalties'],
                    'related_laws': traffic_meta['related_laws'],
                    'blood_alcohol': traffic_meta['blood_alcohol'],
                    'penalty_details': traffic_meta['penalty_details']
                })

                traffic_docs.append(doc)

        print(f"  ✓ 교통법 관련 문서: {len(traffic_docs)}개")
        print(f"  필터링 비율: {len(traffic_docs)/len(all_docs)*100:.1f}%\n")

        # 통계 출력
        self._print_traffic_stats(traffic_docs)

        return traffic_docs

    def load_with_enrichment(
        self,
        db_client: PostgreSQLClient,
        use_source: bool = True,
        use_labeled: bool = True,
        source_types: List[str] = None,
        labeled_types: List[str] = None,
        max_per_type: int = None,
        split: str = 'training',
        traffic_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Load data with PostgreSQL context enrichment.

        Args:
            db_client: PostgreSQL client
            use_source: Use source data
            use_labeled: Use labeled data
            source_types: Source data types
            labeled_types: Labeled data types
            max_per_type: Max documents per type
            split: Data split
            traffic_only: Filter to traffic-related only

        Returns:
            List of enriched documents
        """
        print("\n" + "="*60)
        print("📚 데이터 로딩 with PostgreSQL Context Enrichment")
        print("="*60 + "\n")

        self.set_db_client(db_client)

        # 데이터 로드
        if traffic_only:
            documents = self.load_traffic_only(
                use_source=use_source,
                use_labeled=use_labeled,
                source_types=source_types,
                labeled_types=labeled_types,
                max_per_type=max_per_type,
                split=split
            )
        else:
            documents = self.load_dataset(
                use_source=use_source,
                use_labeled=use_labeled,
                source_types=source_types,
                labeled_types=labeled_types,
                max_per_type=max_per_type,
                split=split
            )

        print(f"\n🔗 PostgreSQL 컨텍스트 추가 중...")

        # QA 데이터에 대해 원문 컨텍스트 추가
        enriched_count = 0

        for doc in documents:
            metadata = doc.get('metadata', {})
            doc_type = metadata.get('type', '')

            # QA 데이터만 컨텍스트 추가
            if '_QA' in doc_type:
                context = self._get_source_context(metadata)
                if context:
                    # 컨텐츠 앞에 컨텍스트 추가
                    doc['content'] = f"[참고 자료]\n{context}\n\n{doc['content']}"
                    metadata['has_context'] = True
                    enriched_count += 1

        print(f"  ✓ 컨텍스트 추가 완료: {enriched_count}개\n")

        return documents

    def _get_source_context(self, metadata: Dict[str, Any]) -> str:
        """
        Get source context from PostgreSQL.

        Args:
            metadata: Document metadata

        Returns:
            Source context text
        """
        if not self.db_client:
            return ""

        doc_id = metadata.get('doc_id', '')
        doc_type = metadata.get('type', '')

        try:
            # 법령 QA
            if '법령_QA' in doc_type:
                article_data = self.db_client.get_law_article(doc_id)
                if article_data:
                    content = article_data.get('content', '')
                    return content[:300] + ('...' if len(content) > 300 else '')

            # 판결문 QA
            elif '판결문_QA' in doc_type:
                section_content = self.db_client.get_precedent_section(doc_id, 'summary')
                if section_content:
                    return section_content[:300] + ('...' if len(section_content) > 300 else '')

        except Exception as e:
            # 조용히 스킵
            pass

        return ""

    def _print_traffic_stats(self, documents: List[Dict[str, Any]]):
        """
        Print traffic law statistics.

        Args:
            documents: List of traffic documents
        """
        from collections import Counter

        print("📊 교통법 데이터 통계:")
        print("-" * 40)

        # 위반 유형 통계
        violation_types = []
        accident_types = []
        penalties = []

        for doc in documents:
            metadata = doc.get('metadata', {})
            violation_types.extend(metadata.get('violation_types', []))
            accident_types.extend(metadata.get('accident_types', []))
            penalties.extend(metadata.get('penalties', []))

        # Top 5 출력
        if violation_types:
            print("\n위반 유형 (Top 5):")
            for vtype, count in Counter(violation_types).most_common(5):
                print(f"  - {vtype}: {count}건")

        if accident_types:
            print("\n사고 유형 (Top 5):")
            for atype, count in Counter(accident_types).most_common(5):
                print(f"  - {atype}: {count}건")

        if penalties:
            print("\n처벌 유형 (Top 5):")
            for ptype, count in Counter(penalties).most_common(5):
                print(f"  - {ptype}: {count}건")

        print("-" * 40 + "\n")

    def get_traffic_stats_summary(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get traffic law statistics summary.

        Args:
            documents: List of traffic documents

        Returns:
            Statistics dictionary
        """
        from collections import Counter

        stats = {
            'total_documents': len(documents),
            'violation_types': {},
            'accident_types': {},
            'penalties': {},
            'blood_alcohol_range': {'min': None, 'max': None, 'avg': None}
        }

        violation_types = []
        accident_types = []
        penalties = []
        blood_alcohols = []

        for doc in documents:
            metadata = doc.get('metadata', {})
            violation_types.extend(metadata.get('violation_types', []))
            accident_types.extend(metadata.get('accident_types', []))
            penalties.extend(metadata.get('penalties', []))

            bac = metadata.get('blood_alcohol')
            if bac:
                blood_alcohols.append(bac)

        stats['violation_types'] = dict(Counter(violation_types))
        stats['accident_types'] = dict(Counter(accident_types))
        stats['penalties'] = dict(Counter(penalties))

        if blood_alcohols:
            stats['blood_alcohol_range'] = {
                'min': min(blood_alcohols),
                'max': max(blood_alcohols),
                'avg': sum(blood_alcohols) / len(blood_alcohols),
                'count': len(blood_alcohols)
            }

        return stats

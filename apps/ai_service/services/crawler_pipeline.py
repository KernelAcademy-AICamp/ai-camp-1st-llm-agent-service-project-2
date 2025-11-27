"""
Crawler Pipeline Service
크롤링 → Precedent 저장 → ChromaDB/BM25 인덱싱 파이프라인
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from services.crawler import CourtPrecedentCrawler, CrawlDocument, CrawlResult
from services.precedent_indexer import PrecedentIndexer
from models.precedent import Precedent
from models.database import write_async_session

from libs.rag_core import (
    KoreanLegalEmbedder,
    ChromaVectorDB,
    BM25Index,
)

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """파이프라인 실행 결과"""
    success: bool
    crawled_count: int = 0
    new_count: int = 0
    duplicate_count: int = 0
    indexed_count: int = 0
    errors: List[str] = []
    metadata: Dict[str, Any] = {}


class CrawlerPipeline:
    """
    크롤러 파이프라인

    전체 흐름:
    1. CourtPrecedentCrawler로 판례 크롤링
    2. case_number로 중복 체크
    3. 새 판례를 Precedent 모델에 저장
    4. PrecedentIndexer로 ChromaDB/BM25 인덱싱
    """

    def __init__(
        self,
        embedder: KoreanLegalEmbedder,
        vectordb: ChromaVectorDB,
        bm25_index: BM25Index,
        crawler_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize crawler pipeline

        Args:
            embedder: Korean legal embedder
            vectordb: ChromaDB instance
            bm25_index: BM25 index instance
            crawler_config: Crawler configuration (oc, timeout, use_mock 등)
        """
        self.crawler = CourtPrecedentCrawler(config=crawler_config or {})
        self.indexer = PrecedentIndexer(
            embedder=embedder,
            vectordb=vectordb,
            bm25_index=bm25_index
        )
        self.embedder = embedder
        self.vectordb = vectordb
        self.bm25_index = bm25_index

        logger.info("CrawlerPipeline initialized")

    async def run_full_pipeline(
        self,
        keyword: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        page: int = 1,
        display: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        court: Optional[str] = None,
        fetch_content: bool = True
    ) -> PipelineResult:
        """
        전체 파이프라인 실행

        Args:
            keyword: 검색 키워드 (단일)
            keywords: 검색 키워드 목록
            page: 페이지 번호
            display: 결과 개수 (최대 100)
            start_date: 선고일자 시작 (YYYY-MM-DD)
            end_date: 선고일자 종료 (YYYY-MM-DD)
            court: 법원명 필터
            fetch_content: 본문 상세 조회 여부

        Returns:
            PipelineResult: 파이프라인 실행 결과
        """
        errors = []
        crawled_docs: List[CrawlDocument] = []

        # 키워드 목록 준비
        search_keywords = keywords or ([keyword] if keyword else [])

        if not search_keywords:
            # 키워드 없이 전체 검색
            search_keywords = [None]

        try:
            # 1. 크롤링 실행
            logger.info(f"Starting crawl with keywords: {search_keywords}")

            for kw in search_keywords:
                filters = {
                    'keyword': kw,
                    'page': page,
                    'display': display,
                    'fetch_content': fetch_content
                }

                if start_date:
                    filters['start_date'] = start_date
                if end_date:
                    filters['end_date'] = end_date
                if court:
                    filters['court'] = court

                result = await self.crawler.crawl(filters=filters)

                if result.success:
                    # metadata에서 documents 추출
                    docs_data = result.metadata.get('documents', [])
                    for doc_data in docs_data:
                        crawled_docs.append(CrawlDocument(**doc_data))
                else:
                    errors.extend(result.errors)

            crawled_count = len(crawled_docs)
            logger.info(f"Crawled {crawled_count} documents")

            if crawled_count == 0:
                return PipelineResult(
                    success=True,
                    crawled_count=0,
                    new_count=0,
                    duplicate_count=0,
                    indexed_count=0,
                    errors=errors,
                    metadata={'message': 'No documents to process'}
                )

            # 2. 중복 체크 및 저장
            new_count = 0
            duplicate_count = 0
            saved_precedents = []

            async with write_async_session() as session:
                for doc in crawled_docs:
                    case_number = doc.metadata.get('case_number', '')

                    if not case_number:
                        errors.append(f"Missing case_number for: {doc.title}")
                        continue

                    # 중복 체크
                    is_duplicate = await self._check_duplicate(session, case_number)

                    if is_duplicate:
                        duplicate_count += 1
                        logger.debug(f"Duplicate found: {case_number}")
                        continue

                    # Precedent 모델에 저장
                    precedent = await self._save_to_precedent(session, doc)
                    if precedent:
                        saved_precedents.append({
                            'case_number': case_number,
                            'title': doc.title,
                            'content': doc.content,
                            'metadata': doc.metadata
                        })
                        new_count += 1

                # 커밋
                await session.commit()
                logger.info(f"Saved {new_count} new precedents, {duplicate_count} duplicates skipped")

            # 3. 인덱싱
            indexed_count = 0
            if saved_precedents:
                index_result = await self.indexer.index_batch(saved_precedents)
                indexed_count = index_result.get('indexed_count', 0)

                if index_result.get('errors'):
                    errors.extend([str(e) for e in index_result['errors'][:5]])

            return PipelineResult(
                success=len(errors) == 0,
                crawled_count=crawled_count,
                new_count=new_count,
                duplicate_count=duplicate_count,
                indexed_count=indexed_count,
                errors=errors[:10],
                metadata={
                    'keywords': search_keywords,
                    'page': page,
                    'chromadb_total': self.vectordb.get_count(),
                    'bm25_total': len(self.bm25_index.documents)
                }
            )

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            errors.append(str(e))
            return PipelineResult(
                success=False,
                crawled_count=len(crawled_docs),
                errors=errors,
                metadata={'error': str(e)}
            )

    async def _check_duplicate(
        self,
        session: AsyncSession,
        case_number: str
    ) -> bool:
        """case_number로 중복 체크"""
        result = await session.execute(
            select(func.count(Precedent.id)).where(
                Precedent.case_number == case_number
            )
        )
        count = result.scalar()
        return count > 0

    async def _save_to_precedent(
        self,
        session: AsyncSession,
        doc: CrawlDocument
    ) -> Optional[Precedent]:
        """CrawlDocument를 Precedent 모델에 저장"""
        try:
            metadata = doc.metadata

            # 선고일자 파싱
            decision_date_str = metadata.get('decision_date', '')
            decision_date = datetime.now()

            if decision_date_str:
                try:
                    # YYYY-MM-DD 또는 YYYYMMDD 형식 처리
                    clean_date = decision_date_str.replace('-', '')
                    if len(clean_date) >= 8:
                        decision_date = datetime.strptime(clean_date[:8], '%Y%m%d')
                except ValueError:
                    logger.warning(f"Invalid date format: {decision_date_str}")

            precedent = Precedent(
                case_number=metadata.get('case_number', ''),
                title=doc.title[:500],
                summary=doc.content[:2000] if doc.content else None,
                full_text=doc.content,
                judgment_summary=self._extract_judgment_summary(doc.content),
                precedent_id=metadata.get('prec_id'),
                court=metadata.get('court', '대법원'),
                decision_date=decision_date,
                case_type=metadata.get('case_type', '형사'),
                case_link=doc.source_url,
                reference_statutes='[]',
                reference_precedents='[]',
                specialization_tags='[]',
            )

            session.add(precedent)
            await session.flush()  # ID 할당

            logger.debug(f"Saved precedent: {precedent.case_number}")
            return precedent

        except Exception as e:
            logger.error(f"Error saving precedent: {e}", exc_info=True)
            return None

    def _extract_judgment_summary(self, content: str) -> Optional[str]:
        """본문에서 판시사항 추출"""
        if not content:
            return None

        # 【판시사항】 섹션 찾기
        start_marker = '【판시사항】'
        end_markers = ['【판결요지】', '【참조조문】', '【참조판례】', '【판례내용】']

        if start_marker not in content:
            return None

        start_idx = content.find(start_marker) + len(start_marker)
        end_idx = len(content)

        for marker in end_markers:
            idx = content.find(marker, start_idx)
            if idx != -1 and idx < end_idx:
                end_idx = idx

        return content[start_idx:end_idx].strip()[:2000]

    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """파이프라인 통계 조회"""
        async with write_async_session() as session:
            result = await session.execute(
                select(func.count(Precedent.id))
            )
            precedent_count = result.scalar()

        return {
            'precedent_count': precedent_count,
            'chromadb_count': self.vectordb.get_count(),
            'bm25_count': len(self.bm25_index.documents),
            'embedding_dimension': self.embedder.get_embedding_dimension()
        }

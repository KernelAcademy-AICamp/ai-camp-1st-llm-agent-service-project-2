#!/usr/bin/env python3
"""
ChromaDB 임베딩 생성 스크립트

통합 교통 데이터를 ChromaDB에 저장하고 임베딩 생성
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

import chromadb
from chromadb.config import Settings
from openai import OpenAI

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChromaDBEmbeddingCreator:
    """ChromaDB 임베딩 생성 클래스"""

    def __init__(self, openai_api_key: str, chroma_persist_dir: str = "./chroma_db"):
        """
        초기화

        Args:
            openai_api_key: OpenAI API 키
            chroma_persist_dir: ChromaDB 영속성 디렉토리
        """
        self.openai_client = OpenAI(api_key=openai_api_key)

        # ChromaDB 클라이언트 생성 (영속성 활성화)
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )

        logger.info(f"ChromaDB 초기화 완료: {chroma_persist_dir}")

        self.embedding_model = "text-embedding-3-small"
        self.collection_name = "traffic_legal_cases"

    def create_collection(self, reset: bool = False):
        """
        ChromaDB 컬렉션 생성

        Args:
            reset: True면 기존 컬렉션 삭제 후 재생성
        """
        # 기존 컬렉션 확인
        collections = self.chroma_client.list_collections()
        collection_exists = any(c.name == self.collection_name for c in collections)

        if collection_exists:
            if reset:
                logger.warning(f"기존 컬렉션 '{self.collection_name}' 삭제 중...")
                self.chroma_client.delete_collection(self.collection_name)
                logger.info("기존 컬렉션 삭제 완료")
            else:
                logger.info(f"기존 컬렉션 '{self.collection_name}' 사용")
                self.collection = self.chroma_client.get_collection(self.collection_name)
                return

        # 새 컬렉션 생성
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"description": "교통 관련 법률 케이스"}
        )
        logger.info(f"새 컬렉션 '{self.collection_name}' 생성 완료")

    def create_embedding(self, text: str) -> List[float]:
        """
        OpenAI API로 임베딩 생성

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (1536차원)
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text[:8000]  # 최대 8000자 제한
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise

    def prepare_document_text(self, case: Dict[str, Any]) -> str:
        """
        케이스 데이터를 임베딩용 텍스트로 변환

        Args:
            case: 판례/법령 데이터

        Returns:
            임베딩용 텍스트
        """
        상세정보 = case.get('상세정보', {})

        # 텍스트 조합 (우선순위: 전문 > 판결요지 > 이유)
        parts = []

        # 1. 사건 정보
        parts.append(f"사건번호: {case.get('사건번호', '')}")
        parts.append(f"법원: {case.get('법원명', '')}")
        parts.append(f"선고일자: {case.get('선고일자', '')}")

        # 2. 판시사항 (있으면)
        if 상세정보.get('판시사항'):
            parts.append(f"판시사항: {상세정보['판시사항']}")

        # 3. 판결요지
        if 상세정보.get('판결요지'):
            parts.append(f"판결요지: {상세정보['판결요지']}")

        # 4. 이유 (있으면)
        if 상세정보.get('이유'):
            parts.append(f"이유: {상세정보['이유'][:2000]}")  # 이유는 길어서 2000자만

        # 5. 전문 (있으면, 일부만)
        if 상세정보.get('전문'):
            parts.append(f"전문: {상세정보['전문'][:3000]}")  # 전문은 3000자만

        # 6. 참조조문
        if 상세정보.get('참조조문'):
            parts.append(f"참조조문: {상세정보['참조조문']}")

        return "\n\n".join(parts)

    def add_cases_to_chromadb(
        self,
        cases: List[Dict[str, Any]],
        case_type: str,
        batch_size: int = 100
    ):
        """
        케이스 데이터를 ChromaDB에 추가

        Args:
            cases: 케이스 리스트
            case_type: 케이스 타입 (판례, 결정례, 해석례, 법령)
            batch_size: 배치 크기
        """
        total = len(cases)
        logger.info(f"\n{'='*60}")
        logger.info(f"{case_type} 임베딩 생성 시작: {total}건")
        logger.info(f"{'='*60}")

        for i in range(0, total, batch_size):
            batch = cases[i:i+batch_size]
            batch_end = min(i+batch_size, total)

            logger.info(f"배치 처리 중: {i+1}~{batch_end}/{total}")

            # 배치 데이터 준비
            ids = []
            embeddings = []
            metadatas = []
            documents = []

            for idx, case in enumerate(batch):
                # ID 생성
                case_id = f"{case_type}_{case.get('판례일련번호', i+idx)}"
                ids.append(case_id)

                # 문서 텍스트 준비
                doc_text = self.prepare_document_text(case)
                documents.append(doc_text)

                # 임베딩 생성
                try:
                    embedding = self.create_embedding(doc_text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"케이스 {case_id} 임베딩 실패: {e}")
                    continue

                # 메타데이터 준비
                metadata = {
                    "case_type": case_type,
                    "사건번호": case.get('사건번호', ''),
                    "법원명": case.get('법원명', ''),
                    "선고일자": case.get('선고일자', ''),
                    "판례일련번호": str(case.get('판례일련번호', '')),
                    "판결요지": case.get('상세정보', {}).get('판결요지', '')[:500],  # 500자만
                    "CSV존재여부": str(case.get('메타데이터', {}).get('CSV존재여부', False))
                }
                metadatas.append(metadata)

            # ChromaDB에 배치 추가
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
                logger.info(f"✅ 배치 저장 완료: {len(ids)}건")
            except Exception as e:
                logger.error(f"배치 저장 실패: {e}")

        logger.info(f"{case_type} 임베딩 생성 완료: {total}건\n")

    def process_unified_data(self, unified_file: str):
        """
        통합 데이터 파일 처리

        Args:
            unified_file: 통합 데이터 JSON 파일 경로
        """
        logger.info(f"통합 데이터 로드 중: {unified_file}")

        with open(unified_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"데이터 로드 완료")
        logger.info(f"수집정보: {data.get('수집정보', {})}")

        # 각 타입별 처리
        case_types = ['판례', '결정례', '해석례', '법령']

        for case_type in case_types:
            if case_type in data and data[case_type]:
                self.add_cases_to_chromadb(data[case_type], case_type)

        # 최종 통계
        collection_count = self.collection.count()
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 전체 임베딩 생성 완료")
        logger.info(f"{'='*60}")
        logger.info(f"ChromaDB 총 벡터 수: {collection_count}")
        logger.info(f"컬렉션 이름: {self.collection_name}")
        logger.info(f"{'='*60}\n")

    def test_search(self, query: str, top_k: int = 5):
        """
        테스트 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트 검색: {query}")
        logger.info(f"{'='*60}")

        # 쿼리 임베딩 생성
        query_embedding = self.create_embedding(query)

        # ChromaDB 검색
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"]
        )

        # 결과 출력
        for i, (metadata, document, distance) in enumerate(zip(
            results['metadatas'][0],
            results['documents'][0],
            results['distances'][0]
        )):
            logger.info(f"\n--- 결과 {i+1} ---")
            logger.info(f"유사도 거리: {distance:.4f}")
            logger.info(f"타입: {metadata.get('case_type')}")
            logger.info(f"사건번호: {metadata.get('사건번호')}")
            logger.info(f"법원명: {metadata.get('법원명')}")
            logger.info(f"판결요지: {metadata.get('판결요지')[:200]}...")

        logger.info(f"\n{'='*60}\n")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="ChromaDB 임베딩 생성")
    parser.add_argument(
        'unified_file',
        help='통합 데이터 JSON 파일 경로'
    )
    parser.add_argument(
        '--openai-api-key',
        help='OpenAI API 키 (환경변수 OPENAI_API_KEY 사용 가능)',
        default=os.getenv('OPENAI_API_KEY')
    )
    parser.add_argument(
        '--chroma-dir',
        help='ChromaDB 저장 디렉토리',
        default='./chroma_db'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='기존 컬렉션 삭제 후 재생성'
    )
    parser.add_argument(
        '--test-query',
        help='완료 후 테스트 검색 쿼리',
        default='무보험 차량 교통사고'
    )

    args = parser.parse_args()

    # API 키 확인
    if not args.openai_api_key:
        logger.error("OpenAI API 키가 필요합니다. --openai-api-key 또는 환경변수 OPENAI_API_KEY 설정")
        sys.exit(1)

    # 파일 존재 확인
    if not os.path.exists(args.unified_file):
        logger.error(f"파일을 찾을 수 없습니다: {args.unified_file}")
        sys.exit(1)

    try:
        # 임베딩 생성기 초기화
        creator = ChromaDBEmbeddingCreator(
            openai_api_key=args.openai_api_key,
            chroma_persist_dir=args.chroma_dir
        )

        # 컬렉션 생성
        creator.create_collection(reset=args.reset)

        # 데이터 처리
        start_time = datetime.now()
        creator.process_unified_data(args.unified_file)
        end_time = datetime.now()

        logger.info(f"총 처리 시간: {end_time - start_time}")

        # 테스트 검색
        if args.test_query:
            creator.test_search(args.test_query)

        logger.info("✅ 모든 작업 완료!")

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

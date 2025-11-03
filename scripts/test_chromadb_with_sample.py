#!/usr/bin/env python3
"""
ChromaDB 샘플 테스트 스크립트

소량의 샘플 데이터로 ChromaDB 기능 테스트
"""

import json
import sys
import os

# 상위 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.create_embeddings_chromadb import ChromaDBEmbeddingCreator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_data(unified_file: str, sample_size: int = 20) -> dict:
    """
    통합 데이터에서 샘플 추출

    Args:
        unified_file: 통합 데이터 파일
        sample_size: 샘플 크기

    Returns:
        샘플 데이터
    """
    logger.info(f"샘플 데이터 추출 중: {sample_size}건")

    with open(unified_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sample_data = {
        "수집정보": data.get("수집정보", {}),
        "판례": data.get("판례", [])[:sample_size],
        "결정례": [],
        "해석례": [],
        "법령": []
    }

    logger.info(f"샘플 추출 완료: 판례 {len(sample_data['판례'])}건")

    return sample_data


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="ChromaDB 샘플 테스트")
    parser.add_argument(
        '--unified-file',
        default='unified_traffic_data/unified_traffic_data_20251103_174822.json',
        help='통합 데이터 JSON 파일 경로'
    )
    parser.add_argument(
        '--openai-api-key',
        help='OpenAI API 키',
        default=os.getenv('OPENAI_API_KEY')
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=20,
        help='샘플 크기 (기본: 20건)'
    )
    parser.add_argument(
        '--chroma-dir',
        default='./chroma_db_test',
        help='ChromaDB 테스트 디렉토리'
    )

    args = parser.parse_args()

    # API 키 확인
    if not args.openai_api_key:
        logger.error("OpenAI API 키가 필요합니다.")
        logger.info("방법 1: --openai-api-key 옵션")
        logger.info("방법 2: 환경변수 OPENAI_API_KEY 설정")
        logger.info("   export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    # 파일 존재 확인
    if not os.path.exists(args.unified_file):
        logger.error(f"파일을 찾을 수 없습니다: {args.unified_file}")
        sys.exit(1)

    try:
        # 1. 샘플 데이터 생성
        sample_data = create_sample_data(args.unified_file, args.sample_size)

        # 임시 샘플 파일 저장
        sample_file = "temp_sample_data.json"
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)

        logger.info(f"샘플 파일 저장: {sample_file}")

        # 2. ChromaDB 임베딩 생성기 초기화
        creator = ChromaDBEmbeddingCreator(
            openai_api_key=args.openai_api_key,
            chroma_persist_dir=args.chroma_dir
        )

        # 3. 컬렉션 생성 (기존 삭제)
        creator.create_collection(reset=True)

        # 4. 샘플 데이터 처리
        creator.process_unified_data(sample_file)

        # 5. 테스트 쿼리들
        test_queries = [
            "무보험 차량 교통사고",
            "음주운전 처벌",
            "신호위반 벌금",
            "중앙선 침범 사고",
            "교통사고처리특례법 적용"
        ]

        logger.info(f"\n{'='*60}")
        logger.info("테스트 쿼리 실행")
        logger.info(f"{'='*60}\n")

        for query in test_queries:
            creator.test_search(query, top_k=3)

        # 6. 샘플 파일 삭제
        os.remove(sample_file)
        logger.info(f"임시 파일 삭제: {sample_file}")

        logger.info("\n✅ 샘플 테스트 완료!")
        logger.info(f"ChromaDB 디렉토리: {args.chroma_dir}")
        logger.info(f"컬렉션: {creator.collection_name}")
        logger.info(f"총 벡터: {creator.collection.count()}개")

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

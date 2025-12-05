#!/usr/bin/env python3
"""
Qdrant 고유 기능 벤치마크

ChromaDB에 없는 Qdrant 고유 기능을 테스트하고,
실제 법률 AI 서비스에서 어떻게 활용할 수 있는지 보여줍니다.

테스트 항목:
1. 필터 기반 검색 (벡터 + 메타데이터 동시)
2. 그룹별 검색 (같은 문서의 청크 그룹화)
3. 페이로드 인덱싱 (검색 속도 향상)
4. 선택적 삭제/업데이트 (특정 문서만 재인덱싱)
5. Scroll API (대용량 데이터 페이지네이션)
"""

import sys
import time
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Project path setup
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition,
    MatchValue, MatchAny, Range, PayloadSchemaType, SearchRequest,
    SearchParams
)
from embeddings.remote_embedder import RemoteEmbedder


# ============================================================
# 테스트 설정
# ============================================================

QDRANT_URL = "http://localhost:6333"
TEST_COLLECTION = "qdrant_feature_test"
EMBEDDING_DIM = 1024


# ============================================================
# 테스트 데이터 생성
# ============================================================

def create_test_data() -> List[Dict]:
    """법률 문서 테스트 데이터 생성"""
    documents = [
        # 판결문 - 음주운전
        {"doc_id": "case_001", "doc_type": "판결문", "section": "이유",
         "text": "피고인은 혈중알코올농도 0.12%의 만취 상태에서 약 2km를 운전하였다. 이는 도로교통법 제44조를 위반한 것이다.",
         "case_type": "음주운전", "year": 2023},
        {"doc_id": "case_001", "doc_type": "판결문", "section": "주문",
         "text": "피고인을 벌금 500만 원에 처한다.",
         "case_type": "음주운전", "year": 2023},
        {"doc_id": "case_001", "doc_type": "판결문", "section": "참조조문",
         "text": "도로교통법 제44조, 제148조의2 제3항 제1호",
         "case_type": "음주운전", "year": 2023},

        # 판결문 - 사기
        {"doc_id": "case_002", "doc_type": "판결문", "section": "이유",
         "text": "사기죄의 주관적 구성요건인 편취의 범의는 미필적 고의로도 족하다. 피고인은 변제할 의사나 능력이 없음에도 피해자를 기망하였다.",
         "case_type": "사기", "year": 2023},
        {"doc_id": "case_002", "doc_type": "판결문", "section": "주문",
         "text": "피고인을 징역 1년에 처한다.",
         "case_type": "사기", "year": 2023},

        # 판결문 - 폭행
        {"doc_id": "case_003", "doc_type": "판결문", "section": "이유",
         "text": "폭행죄와 상해죄의 구별은 피해자의 신체 완전성 훼손 여부에 따른다. 단순한 물리력 행사는 폭행죄에 해당한다.",
         "case_type": "폭행", "year": 2022},
        {"doc_id": "case_003", "doc_type": "판결문", "section": "판시사항",
         "text": "극히 경미한 상처로서 자연적으로 치유되는 경우 상해죄의 상해에 해당하지 않음",
         "case_type": "폭행", "year": 2022},

        # 결정례
        {"doc_id": "decision_001", "doc_type": "결정례", "section": "결정요지",
         "text": "정당방위가 성립하려면 현재의 부당한 침해에 대한 방위행위여야 한다.",
         "case_type": "정당방위", "year": 2024},
        {"doc_id": "decision_001", "doc_type": "결정례", "section": "이유",
         "text": "침해행위가 종료된 후의 반격은 정당방위가 아니라 사후보복에 해당한다.",
         "case_type": "정당방위", "year": 2024},

        # 법령
        {"doc_id": "law_001", "doc_type": "법령", "section": "조문",
         "text": "도로교통법 제44조(술에 취한 상태에서의 운전 금지) 누구든지 술에 취한 상태에서 자동차를 운전하여서는 아니 된다.",
         "case_type": "교통", "year": 2024},
        {"doc_id": "law_002", "doc_type": "법령", "section": "조문",
         "text": "형법 제347조(사기) 사람을 기망하여 재물의 교부를 받거나 재산상의 이익을 취득한 자는 10년 이하의 징역 또는 2천만원 이하의 벌금에 처한다.",
         "case_type": "재산범죄", "year": 2024},
    ]
    return documents


# ============================================================
# 1. 필터 기반 검색 테스트
# ============================================================

def test_filtered_search(client: QdrantClient, embedder: RemoteEmbedder):
    """
    ✅ Qdrant 고유 기능: 벡터 검색 + 메타데이터 필터 동시 적용

    ChromaDB는 where 필터를 지원하지만, Qdrant는 더 복잡한 조건 지원:
    - must, should, must_not 조합
    - 범위 조건 (Range)
    - 중첩 필터
    """
    print("\n" + "=" * 70)
    print("🔍 테스트 1: 필터 기반 검색 (벡터 + 메타데이터)")
    print("=" * 70)

    query = "음주운전 처벌 기준"
    query_emb = embedder.embed_documents([query])[0]

    # 1-1. 필터 없이 검색
    print("\n[1-1] 필터 없이 검색")
    start = time.time()
    results_no_filter = client.query_points(
        collection_name=TEST_COLLECTION,
        query=query_emb,
        limit=5,
        with_payload=True
    )
    time_no_filter = time.time() - start

    print(f"  검색 시간: {time_no_filter*1000:.2f}ms")
    for i, p in enumerate(results_no_filter.points[:3]):
        print(f"  #{i+1} [{p.payload.get('doc_type')}] {p.payload.get('text', '')[:50]}... (score: {p.score:.4f})")

    # 1-2. doc_type='판결문' 필터
    print("\n[1-2] 판결문만 검색 (doc_type='판결문')")
    start = time.time()
    results_type_filter = client.query_points(
        collection_name=TEST_COLLECTION,
        query=query_emb,
        query_filter=Filter(
            must=[FieldCondition(key="doc_type", match=MatchValue(value="판결문"))]
        ),
        limit=5,
        with_payload=True
    )
    time_type_filter = time.time() - start

    print(f"  검색 시간: {time_type_filter*1000:.2f}ms")
    for i, p in enumerate(results_type_filter.points[:3]):
        print(f"  #{i+1} [{p.payload.get('doc_type')}] {p.payload.get('text', '')[:50]}... (score: {p.score:.4f})")

    # 1-3. section='이유' AND year >= 2023
    print("\n[1-3] 복합 필터: section='이유' AND year >= 2023")
    start = time.time()
    results_complex_filter = client.query_points(
        collection_name=TEST_COLLECTION,
        query=query_emb,
        query_filter=Filter(
            must=[
                FieldCondition(key="section", match=MatchValue(value="이유")),
                FieldCondition(key="year", range=Range(gte=2023))
            ]
        ),
        limit=5,
        with_payload=True
    )
    time_complex_filter = time.time() - start

    print(f"  검색 시간: {time_complex_filter*1000:.2f}ms")
    for i, p in enumerate(results_complex_filter.points[:3]):
        print(f"  #{i+1} [{p.payload.get('section')}|{p.payload.get('year')}] {p.payload.get('text', '')[:50]}...")

    # 1-4. OR 조건: doc_type='판결문' OR doc_type='결정례'
    print("\n[1-4] OR 조건: 판결문 OR 결정례")
    start = time.time()
    results_or_filter = client.query_points(
        collection_name=TEST_COLLECTION,
        query=query_emb,
        query_filter=Filter(
            should=[
                FieldCondition(key="doc_type", match=MatchValue(value="판결문")),
                FieldCondition(key="doc_type", match=MatchValue(value="결정례"))
            ]
        ),
        limit=5,
        with_payload=True
    )
    time_or_filter = time.time() - start

    print(f"  검색 시간: {time_or_filter*1000:.2f}ms")

    return {
        "no_filter": {"time_ms": time_no_filter * 1000, "count": len(results_no_filter.points)},
        "type_filter": {"time_ms": time_type_filter * 1000, "count": len(results_type_filter.points)},
        "complex_filter": {"time_ms": time_complex_filter * 1000, "count": len(results_complex_filter.points)},
        "or_filter": {"time_ms": time_or_filter * 1000, "count": len(results_or_filter.points)},
    }


# ============================================================
# 2. 그룹별 검색 테스트
# ============================================================

def test_grouped_search(client: QdrantClient, embedder: RemoteEmbedder):
    """
    ✅ Qdrant 고유 기능: 그룹별 검색 (search_groups)

    같은 문서의 여러 청크 중 대표 청크만 반환
    → 검색 결과에서 중복 문서 제거, 다양한 문서 노출

    ChromaDB에는 이 기능이 없어서 후처리로 중복 제거해야 함
    """
    print("\n" + "=" * 70)
    print("📂 테스트 2: 그룹별 검색 (문서 중복 제거)")
    print("=" * 70)

    query = "법적 처벌 기준"
    query_emb = embedder.embed_documents([query])[0]

    # 2-1. 일반 검색 (같은 문서의 청크가 여러 개 나올 수 있음)
    print("\n[2-1] 일반 검색 (중복 허용)")
    results_normal = client.query_points(
        collection_name=TEST_COLLECTION,
        query=query_emb,
        limit=5,
        with_payload=True
    )

    doc_ids_normal = [p.payload.get('doc_id') for p in results_normal.points]
    print(f"  반환된 doc_id: {doc_ids_normal}")
    print(f"  고유 문서 수: {len(set(doc_ids_normal))}")

    # 2-2. 그룹별 검색 (doc_id 기준 그룹화)
    print("\n[2-2] 그룹별 검색 (doc_id 기준, 문서당 1개)")
    try:
        results_grouped = client.search_groups(
            collection_name=TEST_COLLECTION,
            query_vector=query_emb,
            group_by="doc_id",
            limit=5,  # 반환할 그룹 수
            group_size=1,  # 그룹당 결과 수
            with_payload=True
        )

        print(f"  반환된 그룹 수: {len(results_grouped.groups)}")
        for i, group in enumerate(results_grouped.groups[:5]):
            doc_id = group.id
            if group.hits:
                hit = group.hits[0]
                print(f"  그룹 #{i+1}: {doc_id} - {hit.payload.get('text', '')[:40]}... (score: {hit.score:.4f})")

        return {
            "normal_search": {"unique_docs": len(set(doc_ids_normal)), "total_results": len(doc_ids_normal)},
            "grouped_search": {"groups": len(results_grouped.groups)},
            "feature_available": True
        }
    except Exception as e:
        print(f"  ⚠️ 그룹별 검색 오류: {e}")
        return {"feature_available": False, "error": str(e)}


# ============================================================
# 3. 페이로드 인덱싱 테스트
# ============================================================

def test_payload_indexing(client: QdrantClient, embedder: RemoteEmbedder):
    """
    ✅ Qdrant 고유 기능: 페이로드 인덱싱

    자주 필터링하는 필드에 인덱스를 추가하여 검색 속도 향상
    ChromaDB는 이 기능이 없음
    """
    print("\n" + "=" * 70)
    print("⚡ 테스트 3: 페이로드 인덱싱 (검색 속도 향상)")
    print("=" * 70)

    # 3-1. 현재 인덱스 상태 확인
    print("\n[3-1] 현재 컬렉션 상태")
    collection_info = client.get_collection(TEST_COLLECTION)
    print(f"  포인트 수: {collection_info.points_count}")

    # 3-2. 인덱스 생성
    print("\n[3-2] 페이로드 인덱스 생성")
    try:
        # doc_type 필드에 키워드 인덱스 생성
        client.create_payload_index(
            collection_name=TEST_COLLECTION,
            field_name="doc_type",
            field_schema=PayloadSchemaType.KEYWORD
        )
        print("  ✅ doc_type 인덱스 생성됨")

        # year 필드에 정수 인덱스 생성
        client.create_payload_index(
            collection_name=TEST_COLLECTION,
            field_name="year",
            field_schema=PayloadSchemaType.INTEGER
        )
        print("  ✅ year 인덱스 생성됨")

        # section 필드에 키워드 인덱스 생성
        client.create_payload_index(
            collection_name=TEST_COLLECTION,
            field_name="section",
            field_schema=PayloadSchemaType.KEYWORD
        )
        print("  ✅ section 인덱스 생성됨")

    except Exception as e:
        print(f"  인덱스 이미 존재하거나 오류: {e}")

    # 3-3. 인덱스 사용 후 검색 성능 비교
    print("\n[3-3] 인덱스 활용 검색 성능")
    query = "처벌 기준"
    query_emb = embedder.embed_documents([query])[0]

    # 필터 검색 수행
    times = []
    for _ in range(5):
        start = time.time()
        client.query_points(
            collection_name=TEST_COLLECTION,
            query=query_emb,
            query_filter=Filter(
                must=[
                    FieldCondition(key="doc_type", match=MatchValue(value="판결문")),
                    FieldCondition(key="year", range=Range(gte=2023))
                ]
            ),
            limit=5
        )
        times.append((time.time() - start) * 1000)

    avg_time = np.mean(times)
    print(f"  평균 검색 시간 (5회): {avg_time:.2f}ms")

    return {
        "indexed_fields": ["doc_type", "year", "section"],
        "avg_search_time_ms": avg_time
    }


# ============================================================
# 4. 선택적 삭제/업데이트 테스트
# ============================================================

def test_selective_operations(client: QdrantClient):
    """
    ✅ Qdrant 고유 기능: 필터 기반 삭제/업데이트

    특정 조건의 문서만 삭제하고 재인덱싱 가능
    ChromaDB도 where 필터 삭제를 지원하지만, Qdrant가 더 유연함
    """
    print("\n" + "=" * 70)
    print("🗑️ 테스트 4: 선택적 삭제/업데이트")
    print("=" * 70)

    # 4-1. 조건별 카운트
    print("\n[4-1] 조건별 문서 수 조회")

    count_all = client.count(collection_name=TEST_COLLECTION)
    print(f"  전체: {count_all.count}개")

    count_판결문 = client.count(
        collection_name=TEST_COLLECTION,
        count_filter=Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value="판결문"))])
    )
    print(f"  판결문: {count_판결문.count}개")

    count_2023 = client.count(
        collection_name=TEST_COLLECTION,
        count_filter=Filter(must=[FieldCondition(key="year", range=Range(gte=2023))])
    )
    print(f"  2023년 이후: {count_2023.count}개")

    # 4-2. 다중 조건 카운트
    print("\n[4-2] 복합 조건 카운트")
    count_complex = client.count(
        collection_name=TEST_COLLECTION,
        count_filter=Filter(
            must=[
                FieldCondition(key="doc_type", match=MatchAny(any=["판결문", "결정례"])),
                FieldCondition(key="section", match=MatchValue(value="이유"))
            ]
        )
    )
    print(f"  (판결문 OR 결정례) AND section='이유': {count_complex.count}개")

    return {
        "total": count_all.count,
        "판결문": count_판결문.count,
        "2023_이후": count_2023.count,
        "complex_condition": count_complex.count
    }


# ============================================================
# 5. Scroll API 테스트 (대용량 페이지네이션)
# ============================================================

def test_scroll_api(client: QdrantClient):
    """
    ✅ Qdrant 고유 기능: Scroll API

    대용량 데이터를 페이지 단위로 순회
    ChromaDB의 get()은 메모리에 전부 로드해야 함
    """
    print("\n" + "=" * 70)
    print("📜 테스트 5: Scroll API (대용량 페이지네이션)")
    print("=" * 70)

    # 5-1. 전체 데이터 스크롤
    print("\n[5-1] 전체 데이터 스크롤 (limit=3씩)")

    all_points = []
    offset = None
    page = 0

    while True:
        results, next_offset = client.scroll(
            collection_name=TEST_COLLECTION,
            limit=3,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        page += 1
        print(f"  Page {page}: {len(results)}개 포인트")

        all_points.extend(results)

        if next_offset is None:
            break
        offset = next_offset

    print(f"  총 수집: {len(all_points)}개")

    # 5-2. 필터 + 스크롤
    print("\n[5-2] 필터 + 스크롤 (판결문만)")

    filtered_points = []
    offset = None

    while True:
        results, next_offset = client.scroll(
            collection_name=TEST_COLLECTION,
            scroll_filter=Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value="판결문"))]),
            limit=10,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        filtered_points.extend(results)

        if next_offset is None:
            break
        offset = next_offset

    print(f"  판결문 수집: {len(filtered_points)}개")

    return {
        "total_scrolled": len(all_points),
        "filtered_scrolled": len(filtered_points),
        "pages": page
    }


# ============================================================
# 6. 실제 사용 사례: 같은 판례의 전체 내용 조회
# ============================================================

def test_full_document_retrieval(client: QdrantClient, embedder: RemoteEmbedder):
    """
    ✅ 실제 사용 사례: 검색된 청크의 원본 문서 전체 조회

    1. 벡터 검색으로 관련 청크 찾기
    2. 해당 청크의 doc_id로 같은 문서의 모든 청크 조회
    3. 전체 문서 재구성
    """
    print("\n" + "=" * 70)
    print("📄 테스트 6: 실제 사용 - 전체 문서 조회")
    print("=" * 70)

    # 6-1. 벡터 검색으로 관련 청크 찾기
    query = "음주운전 처벌"
    query_emb = embedder.embed_documents([query])[0]

    print(f"\n[6-1] 쿼리: '{query}'")
    results = client.query_points(
        collection_name=TEST_COLLECTION,
        query=query_emb,
        limit=1,
        with_payload=True
    )

    if not results.points:
        print("  검색 결과 없음")
        return {}

    top_result = results.points[0]
    doc_id = top_result.payload.get('doc_id')
    print(f"  Top-1 문서: {doc_id}")
    print(f"  청크 내용: {top_result.payload.get('text', '')[:50]}...")

    # 6-2. 같은 문서의 모든 청크 조회
    print(f"\n[6-2] '{doc_id}'의 모든 청크 조회")

    all_chunks, _ = client.scroll(
        collection_name=TEST_COLLECTION,
        scroll_filter=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]),
        limit=100,
        with_payload=True,
        with_vectors=False
    )

    print(f"  청크 수: {len(all_chunks)}")

    # 섹션별 정렬
    sections = {}
    for chunk in all_chunks:
        section = chunk.payload.get('section', 'unknown')
        if section not in sections:
            sections[section] = []
        sections[section].append(chunk.payload.get('text', ''))

    print(f"  섹션: {list(sections.keys())}")

    # 6-3. 전체 문서 재구성
    print(f"\n[6-3] 전체 문서 재구성")
    full_text_parts = []
    for section, texts in sections.items():
        full_text_parts.append(f"【{section}】")
        full_text_parts.extend(texts)

    full_text = "\n".join(full_text_parts)
    print(f"  재구성된 문서 길이: {len(full_text)}자")
    print(f"\n  --- 재구성된 문서 ---")
    print(full_text[:500] + "..." if len(full_text) > 500 else full_text)

    return {
        "query": query,
        "found_doc_id": doc_id,
        "chunk_count": len(all_chunks),
        "sections": list(sections.keys()),
        "full_text_length": len(full_text)
    }


# ============================================================
# 메인
# ============================================================

def main():
    print("=" * 70)
    print("🔬 Qdrant 고유 기능 벤치마크")
    print("=" * 70)
    print(f"📅 {datetime.now().isoformat()}")

    # Qdrant 클라이언트 초기화
    client = QdrantClient(url=QDRANT_URL)
    print(f"\n✅ Qdrant 연결: {QDRANT_URL}")

    # 임베더 초기화
    embedder = RemoteEmbedder(model="dragonkue/snowflake-arctic-embed-l-v2.0-ko")

    # 테스트 컬렉션 생성
    print(f"\n📦 테스트 컬렉션 생성: {TEST_COLLECTION}")
    try:
        client.delete_collection(TEST_COLLECTION)
    except:
        pass

    client.create_collection(
        collection_name=TEST_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
    )

    # 테스트 데이터 삽입
    print("\n📝 테스트 데이터 삽입...")
    documents = create_test_data()
    texts = [doc['text'] for doc in documents]
    embeddings = embedder.embed_documents(texts)

    points = []
    for i, (doc, emb) in enumerate(zip(documents, embeddings)):
        points.append(PointStruct(
            id=i,
            vector=emb,
            payload=doc
        ))

    client.upsert(collection_name=TEST_COLLECTION, points=points)
    print(f"  {len(points)}개 포인트 삽입 완료")

    # 테스트 실행
    results = {}

    results['filtered_search'] = test_filtered_search(client, embedder)
    results['grouped_search'] = test_grouped_search(client, embedder)
    results['payload_indexing'] = test_payload_indexing(client, embedder)
    results['selective_operations'] = test_selective_operations(client)
    results['scroll_api'] = test_scroll_api(client)
    results['full_document'] = test_full_document_retrieval(client, embedder)

    # 결과 요약
    print("\n" + "=" * 70)
    print("📊 결과 요약: Qdrant 고유 기능 활용")
    print("=" * 70)

    print("""
┌─────────────────────────────────────────────────────────────────────────┐
│                    Qdrant vs ChromaDB 기능 비교                          │
├─────────────────────────────┬───────────────────┬───────────────────────┤
│         기능                │     Qdrant        │      ChromaDB         │
├─────────────────────────────┼───────────────────┼───────────────────────┤
│ 필터 기반 검색 (must/should)│       ✅          │     ⚠️ 제한적         │
│ 범위 필터 (Range)           │       ✅          │        ❌              │
│ 그룹별 검색 (search_groups) │       ✅          │        ❌              │
│ 페이로드 인덱싱             │       ✅          │        ❌              │
│ Scroll API (페이지네이션)   │       ✅          │     ⚠️ 비효율         │
│ 선택적 삭제 (필터)          │       ✅          │        ✅              │
│ 다중 벡터 타입              │       ✅          │        ❌              │
│ 하이브리드 검색 (Sparse)    │       ✅          │        ❌              │
│ 분산 배포 (Sharding)        │       ✅          │        ❌              │
└─────────────────────────────┴───────────────────┴───────────────────────┘
""")

    print("\n📌 이 프로젝트에서 활용하는 Qdrant 고유 기능:")
    print("  1. 필터 기반 검색: 문서 타입, 연도, 섹션별 필터링")
    print("  2. 그룹별 검색: 같은 판례의 중복 청크 제거")
    print("  3. Scroll API: 대용량 데이터 페이지네이션 (재청킹 시)")
    print("  4. 선택적 삭제: 특정 문서 타입만 재인덱싱")
    print("  5. 페이로드 인덱싱: 자주 필터링하는 필드 속도 향상")

    # 결과 저장
    output_path = Path(__file__).parent / "qdrant_features_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 결과 저장: {output_path}")

    # 정리
    print(f"\n🧹 테스트 컬렉션 삭제: {TEST_COLLECTION}")
    client.delete_collection(TEST_COLLECTION)

    print("\n" + "=" * 70)

    return results


if __name__ == "__main__":
    main()

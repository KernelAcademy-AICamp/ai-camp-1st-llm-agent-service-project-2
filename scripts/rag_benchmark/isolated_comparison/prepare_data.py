#!/usr/bin/env python3
"""
격리된 컴포넌트 비교를 위한 데이터 준비 스크립트

샘플 데이터를 추출하고 두 가지 청킹 전략을 적용한 후
두 가지 임베딩 모델로 임베딩을 생성합니다.

결과:
- 4가지 조합의 임베딩 데이터 생성
  1. 500자 청킹 + ko-sroberta
  2. 500자 청킹 + snowflake-arctic
  3. 법률특화 청킹 + ko-sroberta
  4. 법률특화 청킹 + snowflake-arctic
"""

import sys
import os
import json
import csv
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from tqdm import tqdm

# Add project root to path
BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()


@dataclass
class RawDocument:
    """원본 문서"""
    doc_id: str
    doc_type: str  # 판결문, 결정례
    title: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class Chunk:
    """청크"""
    chunk_id: str
    doc_id: str
    doc_type: str
    text: str
    chunk_index: int
    chunking_strategy: str  # "fixed_500" or "legal_specialized"
    metadata: Dict[str, Any]


# ============================================================
# 1. 데이터 로딩
# ============================================================

def load_raw_documents(
    data_dir: Path,
    doc_types: List[str] = ["TS_판결문", "TS_결정례"],
    sample_size: int = 500
) -> List[RawDocument]:
    """원본 문서 샘플 로딩"""

    documents = []

    for doc_type in doc_types:
        type_dir = data_dir / doc_type
        if not type_dir.exists():
            print(f"⚠️ 디렉토리 없음: {type_dir}")
            continue

        files = list(type_dir.glob("*.csv"))

        # 샘플링
        sample_files = random.sample(files, min(sample_size, len(files)))

        print(f"📂 {doc_type}: {len(sample_files)}개 파일 로딩 중...")

        for file_path in tqdm(sample_files, desc=f"  {doc_type}"):
            try:
                doc = load_single_document(file_path, doc_type.replace("TS_", ""))
                if doc and len(doc.content) > 100:
                    documents.append(doc)
            except Exception as e:
                pass  # 오류 무시

    print(f"✅ 총 {len(documents)}개 문서 로딩 완료")
    return documents


def load_single_document(file_path: Path, doc_type: str) -> RawDocument:
    """단일 문서 로딩"""

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return None

    doc_id = rows[0].get('판례일련번호', file_path.stem)

    # 섹션별로 내용 수집
    sections = {}
    for row in rows:
        section = row.get('구분', 'unknown')
        content = row.get('내용', '')
        if section not in sections:
            sections[section] = []
        sections[section].append(content)

    # 전체 텍스트 구성
    full_text_parts = []
    for section, contents in sections.items():
        if contents:
            full_text_parts.append(f"[{section}]")
            full_text_parts.extend(contents)

    full_text = "\n".join(full_text_parts)

    # 제목 추출 (첫 번째 문장 또는 판시사항)
    title = sections.get('판시사항', [''])[0][:100] if '판시사항' in sections else f"{doc_type}_{doc_id}"

    return RawDocument(
        doc_id=str(doc_id),
        doc_type=doc_type,
        title=title,
        content=full_text,
        metadata={
            "file_path": str(file_path),
            "sections": list(sections.keys())
        }
    )


# ============================================================
# 2. 청킹 전략
# ============================================================

def chunk_fixed_500(doc: RawDocument) -> List[Chunk]:
    """500자 고정 청킹 (Before 전략)"""

    text = doc.content
    chunk_size = 500
    overlap = 50

    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        if len(chunk_text.strip()) > 50:  # 최소 길이 체크
            chunks.append(Chunk(
                chunk_id=f"{doc.doc_id}_fixed_{chunk_idx}",
                doc_id=doc.doc_id,
                doc_type=doc.doc_type,
                text=chunk_text,
                chunk_index=chunk_idx,
                chunking_strategy="fixed_500",
                metadata={
                    "title": doc.title,
                    "start_pos": start,
                    "end_pos": end
                }
            ))
            chunk_idx += 1

        start = end - overlap

    return chunks


def chunk_legal_specialized(doc: RawDocument) -> List[Chunk]:
    """
    법률특화 청킹 (After 전략)
    - 실제 라이브러리의 청킹 전략 사용
    - 판결문/결정례: PrecedentAutoChunking (섹션 자동 감지)
    - 법령: LegalArticleChunking (조문 단위)
    """
    from chunking.legal_chunker import PrecedentAutoChunking, LegalArticleChunking

    text = doc.content
    chunks = []

    # 문서 타입에 따라 적절한 청킹 전략 선택
    if doc.doc_type in ["판결문", "결정례"]:
        # 판결문/결정례: PrecedentAutoChunking
        chunker = PrecedentAutoChunking(
            chunk_size=600,
            overlap=100,
            auto_detect_sections=True
        )
        metadata = {
            "title": doc.title,
            "doc_type": doc.doc_type
        }
    else:
        # 법령: LegalArticleChunking
        chunker = LegalArticleChunking(
            chunk_size=512,
            max_chunk_size=800,
            min_chunk_size=100,
            merge_max_size=600,
            hard_max_size=1500
        )
        metadata = {
            "title": doc.title,
            "doc_type": doc.doc_type
        }

    # 청킹 실행
    raw_chunks = chunker.chunk(text, metadata)

    # Chunk 객체로 변환
    for idx, raw_chunk in enumerate(raw_chunks):
        content = raw_chunk.get('content', '')
        chunk_meta = raw_chunk.get('metadata', {})

        if len(content.strip()) > 30:  # 최소 길이 체크
            chunks.append(Chunk(
                chunk_id=f"{doc.doc_id}_legal_{idx}",
                doc_id=doc.doc_id,
                doc_type=doc.doc_type,
                text=content.strip(),
                chunk_index=idx,
                chunking_strategy="legal_specialized",
                metadata={
                    "title": doc.title,
                    "section": chunk_meta.get('section', ''),
                    "chunk_type": chunk_meta.get('chunk_type', ''),
                    "chunking_strategy": chunk_meta.get('chunking_strategy', 'legal_specialized')
                }
            ))

    # 청크가 없으면 fallback으로 고정 청킹
    if not chunks:
        return chunk_fixed_500(doc)

    return chunks


# ============================================================
# 3. 임베딩 생성
# ============================================================

def embed_with_ko_sroberta(chunks: List[Chunk], batch_size: int = 32) -> List[Tuple[Chunk, np.ndarray]]:
    """ko-sroberta 임베딩"""
    from embeddings.embedder import KoreanLegalEmbedder

    print("🔧 ko-sroberta 임베딩 생성 중...")
    embedder = KoreanLegalEmbedder()

    results = []
    texts = [c.text for c in chunks]

    for i in tqdm(range(0, len(texts), batch_size), desc="  임베딩"):
        batch_texts = texts[i:i+batch_size]
        batch_chunks = chunks[i:i+batch_size]

        embeddings = embedder.embed_documents(batch_texts)

        for chunk, emb in zip(batch_chunks, embeddings):
            results.append((chunk, np.array(emb)))

    print(f"✅ {len(results)}개 청크 임베딩 완료 (768d)")
    return results


def embed_with_snowflake_arctic(chunks: List[Chunk], batch_size: int = 16) -> List[Tuple[Chunk, np.ndarray]]:
    """snowflake-arctic 임베딩 (Remote API)"""
    from embeddings.remote_embedder import RemoteEmbedder

    print("🔧 snowflake-arctic 임베딩 생성 중...")
    embedder = RemoteEmbedder(model="dragonkue/snowflake-arctic-embed-l-v2.0-ko")

    results = []
    texts = [c.text for c in chunks]

    for i in tqdm(range(0, len(texts), batch_size), desc="  임베딩"):
        batch_texts = texts[i:i+batch_size]
        batch_chunks = chunks[i:i+batch_size]

        embeddings = embedder.embed_documents(batch_texts)

        for chunk, emb in zip(batch_chunks, embeddings):
            results.append((chunk, np.array(emb)))

    print(f"✅ {len(results)}개 청크 임베딩 완료 (1024d)")
    return results


# ============================================================
# 4. 저장
# ============================================================

def save_embeddings(
    embedded_chunks: List[Tuple[Chunk, np.ndarray]],
    output_dir: Path,
    name: str
):
    """임베딩 데이터 저장"""

    output_dir.mkdir(parents=True, exist_ok=True)

    # 메타데이터 저장
    metadata_path = output_dir / f"{name}_metadata.json"
    chunks_data = []

    for chunk, _ in embedded_chunks:
        chunks_data.append({
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "doc_type": chunk.doc_type,
            "text": chunk.text,
            "chunk_index": chunk.chunk_index,
            "chunking_strategy": chunk.chunking_strategy,
            "metadata": chunk.metadata
        })

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    # 임베딩 벡터 저장
    embeddings = np.array([emb for _, emb in embedded_chunks])
    embeddings_path = output_dir / f"{name}_embeddings.npy"
    np.save(embeddings_path, embeddings)

    print(f"💾 저장 완료: {name}")
    print(f"   - 메타데이터: {metadata_path}")
    print(f"   - 임베딩: {embeddings_path} (shape: {embeddings.shape})")

    return metadata_path, embeddings_path


# ============================================================
# 5. 메인 실행
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="격리된 컴포넌트 비교용 데이터 준비")
    parser.add_argument("--sample-size", type=int, default=300,
                       help="문서 타입별 샘플 수 (기본: 300)")
    parser.add_argument("--output-dir", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "isolated_comparison" / "data"),
                       help="출력 디렉토리")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드")

    args = parser.parse_args()
    random.seed(args.seed)

    print("=" * 70)
    print("🔬 격리된 컴포넌트 비교용 데이터 준비")
    print("=" * 70)
    print(f"📅 {datetime.now().isoformat()}")
    print(f"📊 샘플 크기: 문서 타입별 {args.sample_size}개")
    print()

    # 데이터 경로
    data_dir = BASE_DIR / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터" / "Training" / "01.원천데이터"
    output_dir = Path(args.output_dir)

    # 1. 원본 문서 로딩
    print("\n📥 [1/5] 원본 문서 로딩...")
    documents = load_raw_documents(
        data_dir,
        doc_types=["TS_판결문", "TS_결정례"],
        sample_size=args.sample_size
    )

    # 2. 청킹
    print("\n✂️ [2/5] 청킹 적용...")

    fixed_chunks = []
    legal_chunks = []

    for doc in tqdm(documents, desc="  청킹"):
        fixed_chunks.extend(chunk_fixed_500(doc))
        legal_chunks.extend(chunk_legal_specialized(doc))

    print(f"   고정 500자 청킹: {len(fixed_chunks)}개 청크")
    print(f"   법률특화 청킹: {len(legal_chunks)}개 청크")

    # 3. 임베딩 생성 (4가지 조합)
    print("\n🔢 [3/5] 임베딩 생성...")

    # 조합 1: 고정청킹 + ko-sroberta
    print("\n  [조합 1] 고정500자 + ko-sroberta")
    fixed_kosroberta = embed_with_ko_sroberta(fixed_chunks)

    # 조합 2: 고정청킹 + snowflake-arctic
    print("\n  [조합 2] 고정500자 + snowflake-arctic")
    fixed_arctic = embed_with_snowflake_arctic(fixed_chunks)

    # 조합 3: 법률특화 + ko-sroberta
    print("\n  [조합 3] 법률특화 + ko-sroberta")
    legal_kosroberta = embed_with_ko_sroberta(legal_chunks)

    # 조합 4: 법률특화 + snowflake-arctic
    print("\n  [조합 4] 법률특화 + snowflake-arctic")
    legal_arctic = embed_with_snowflake_arctic(legal_chunks)

    # 4. 저장
    print("\n💾 [4/5] 데이터 저장...")

    save_embeddings(fixed_kosroberta, output_dir, "fixed_kosroberta")
    save_embeddings(fixed_arctic, output_dir, "fixed_arctic")
    save_embeddings(legal_kosroberta, output_dir, "legal_kosroberta")
    save_embeddings(legal_arctic, output_dir, "legal_arctic")

    # 5. 요약 정보 저장
    print("\n📋 [5/5] 요약 정보 저장...")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "sample_size": args.sample_size,
        "total_documents": len(documents),
        "combinations": {
            "fixed_kosroberta": {
                "chunking": "fixed_500",
                "embedding": "ko-sroberta (768d)",
                "num_chunks": len(fixed_chunks)
            },
            "fixed_arctic": {
                "chunking": "fixed_500",
                "embedding": "snowflake-arctic (1024d)",
                "num_chunks": len(fixed_chunks)
            },
            "legal_kosroberta": {
                "chunking": "legal_specialized",
                "embedding": "ko-sroberta (768d)",
                "num_chunks": len(legal_chunks)
            },
            "legal_arctic": {
                "chunking": "legal_specialized",
                "embedding": "snowflake-arctic (1024d)",
                "num_chunks": len(legal_chunks)
            }
        }
    }

    summary_path = output_dir / "preparation_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 데이터 준비 완료!")
    print(f"📁 출력 디렉토리: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()

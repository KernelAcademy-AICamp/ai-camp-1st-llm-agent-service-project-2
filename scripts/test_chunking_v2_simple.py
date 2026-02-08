# -*- coding: utf-8 -*-
"""
Simple Chunking V2 Test (Windows compatible)
Uses synthetic sample data to verify chunking logic
"""
import sys
import os
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import re


# ============================================================
# SAMPLE DATA (Synthetic data mimicking real data structure)
# ============================================================

SAMPLE_LAW_CONTENT = """[형법 제329조 - 절도]
제329조(절도) 타인의 재물을 절취한 자는 6년 이하의 징역 또는 1천만원 이하의 벌금에 처한다.
① 절도죄의 객체는 타인의 재물이다. 재물이란 관리할 수 있는 동산 및 동력을 말한다.
② 절취란 타인이 점유하는 재물을 그 의사에 반하여 자기 또는 제3자의 점유로 이전하는 행위를 말한다.
③ 본조의 죄는 친고죄가 아니므로 피해자의 고소 없이도 공소를 제기할 수 있다.
④ 미수범은 처벌한다(형법 제342조).
⑤ 야간에 사람의 주거, 관리하는 건조물, 선박이나 항공기 또는 점유하는 방실에 침입하여 타인의 재물을 절취한 자는 10년 이하의 징역에 처한다."""

SAMPLE_LAW_METADATA = {
    'law_id': '013988',
    'article_num': '제329조',
    'article_title': '절도',
    'law_title': '형법',
    'has_structure': True,
    'gubun_used': True,
    'type': 'source_법령'
}

SAMPLE_INTERPRETATION_CONTENT = """[해석례 법제처-2023-001]

[질의요지]
형법 제329조의 절도죄에서 '재물'의 범위에 전기 에너지가 포함되는지 여부 및 전기 절도의 경우 형법 제346조의 특별규정이 적용되는지 여부에 관하여 질의합니다.

[회답]
전기 에너지는 형법 제346조에 의하여 재물로 의제되므로 절도죄의 객체가 될 수 있으며, 전기를 절취한 경우에는 형법 제329조의 절도죄가 아닌 형법 제346조의 규정에 따라 처벌됩니다.

[이유]
1. 형법 제346조는 "본 장의 죄에 있어서 관리할 수 있는 동력은 재물로 간주한다"고 규정하고 있습니다.
2. 전기 에너지는 관리 가능한 동력에 해당하므로 형법상 재물로 취급됩니다.
3. 따라서 전기를 무단으로 사용하는 행위는 절도죄의 구성요건에 해당합니다.
4. 대법원 판례(대법원 2015. 5. 14. 선고 2015도1234 판결)에서도 동일한 취지로 판시하고 있습니다."""

SAMPLE_INTERPRETATION_METADATA = {
    'interpretation_id': '2023-001',
    'has_query': True,
    'has_response': True,
    'has_reason': True,
    'has_structure': True,
    'agenda_num': '법제처-2023-001',
    'type': 'source_해석례'
}

SAMPLE_PRECEDENT_CONTENT = """[대법원 2020도12345 업무상횡령 - 판결내용]

피고인이 회사의 경리담당자로서 근무하던 중 회사 자금 5천만원을 개인 용도로 사용한 사안에서,
원심은 피고인에게 업무상횡령죄를 인정하여 징역 2년을 선고하였다.

대법원은 다음과 같은 이유로 원심판결을 파기환송하였다.

첫째, 업무상횡령죄가 성립하기 위해서는 타인의 재물을 보관하는 자가 그 재물을 횡령하여야 한다.
둘째, 이 사건에서 피고인이 회사 자금을 보관하는 지위에 있었는지 여부가 명확하지 않다.
셋째, 원심은 이 점에 관하여 충분한 심리를 하지 않았다.

따라서 원심판결을 파기하고, 사건을 원심법원에 환송한다."""

SAMPLE_PRECEDENT_METADATA = {
    'precedent_id': '2020-12345',
    'case_num': '2020도12345',
    'case_name': '업무상횡령',
    'section': '판결내용',
    'has_structure': True,
    'court_name': '대법원',
    'type': 'source_판결문'
}

SAMPLE_QA_CONTENT = """[판결문 QA - 2019도5678 특수절도]
Q: 특수절도죄에서 '야간'의 의미는 무엇이며, 해가 진 직후와 뜨기 직전도 야간에 포함되나요?
A: 형법상 '야간'이란 해가 진 후부터 해가 뜨기 전까지의 시간을 말합니다. 따라서 해가 진 직후와 뜨기 직전도 야간에 포함됩니다. 다만, 일몰과 일출 시각은 계절과 지역에 따라 달라지므로, 범행 당시의 구체적인 시간과 장소를 기준으로 판단하여야 합니다. 대법원은 "야간의 판단은 천문학적 일몰·일출 시각을 기준으로 하되, 구체적 사정을 고려하여 사회통념에 따라 판단하여야 한다"고 판시하였습니다(대법원 2018. 3. 15. 선고 2017도18765 판결 참조)."""

SAMPLE_QA_METADATA = {
    'label_type': 'QA',
    'case_num': '2019도5678',
    'case_name': '특수절도',
    'type': 'labeled_판결문_QA'
}

SAMPLE_LONG_CONTENT = """[형법 제250조 - 살인]
제250조(살인, 존속살해) ① 사람을 살해한 자는 사형, 무기 또는 5년 이상의 징역에 처한다.
② 자기 또는 배우자의 직계존속을 살해한 자는 사형, 무기 또는 7년 이상의 징역에 처한다.

살인죄는 형법상 가장 중한 범죄 중 하나로서, 인간의 생명을 보호법익으로 한다. 본죄의 객체는 '사람'이며, 여기서 사람이란 출생부터 사망까지의 생존하는 자연인을 말한다.

살인죄의 구성요건은 다음과 같다:
1. 주체: 자연인이면 누구나 본죄의 주체가 될 수 있다.
2. 객체: 타인, 즉 행위자 이외의 생존하는 자연인이어야 한다.
3. 행위: 사람을 살해하는 것, 즉 생명을 단절시키는 행위를 말한다.
4. 고의: 살인의 고의, 즉 사람을 살해한다는 인식과 의사가 필요하다.

미수범 처벌: 살인미수죄는 형법 제254조에 의하여 처벌된다.
예비·음모죄: 살인죄의 예비 또는 음모를 한 자는 10년 이하의 징역에 처한다(형법 제255조).

판례에 따르면, 살인의 고의는 반드시 살해의 목적이나 계획적인 의도를 요하지 않으며, 자기의 행위로 인하여 타인의 사망이라는 결과를 발생시킬 만한 가능 또는 위험이 있음을 인식하거나 예견하면 족하고, 그 인식이나 예견은 확정적인 것은 물론 불확정적인 것이라도 이른바 미필적 고의로 인정된다(대법원 2000. 8. 18. 선고 2000도2231 판결).

존속살해죄는 자기 또는 배우자의 직계존속에 대한 살인으로서 일반 살인죄보다 형이 가중되어 있다. 이는 유교적 전통에 기반한 효도 관념을 반영한 것이나, 헌법상 평등원칙에 위배된다는 논란이 있다."""


def test_chunking_strategies():
    """Test new chunking strategies with synthetic sample data"""

    # Import chunking strategies
    from libs.rag_core.chunking.legal_chunker import (
        LegalArticleChunking,
        PrecedentAutoChunking,
        InterpretationChunking,
        QAPreserveChunking
    )
    from libs.rag_core.chunking.legal_chunker_v2 import (
        LegalArticleChunkingV2,
        PrecedentChunkingV2,
        InterpretationChunkingV2,
        QAPreserveChunkingV2,
        get_chunker_v2
    )

    print("=" * 60)
    print("Chunking Strategy V2 Test (Synthetic Data)")
    print("=" * 60)
    print("Using synthetic sample data to verify chunking logic")

    # Test 1: 법령 (Law)
    print("\n" + "=" * 60)
    print("TEST 1: Law (법령) Chunking")
    print("=" * 60)

    print(f"\nSample content ({len(SAMPLE_LAW_CONTENT)} chars):")
    print(SAMPLE_LAW_CONTENT[:400] + "...")

    # Test old chunker
    print("\n--- Old Strategy (LegalArticleChunking) ---")
    old_chunker = LegalArticleChunking()
    old_chunks = old_chunker.chunk(SAMPLE_LAW_CONTENT, SAMPLE_LAW_METADATA)
    print(f"Chunks: {len(old_chunks)}")
    for i, c in enumerate(old_chunks[:5]):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunk_type', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test new chunker
    print("\n--- New Strategy V2 (LegalArticleChunkingV2) ---")
    new_chunker = LegalArticleChunkingV2()
    new_chunks = new_chunker.chunk(SAMPLE_LAW_CONTENT, SAMPLE_LAW_METADATA)
    print(f"Chunks: {len(new_chunks)}")
    for i, c in enumerate(new_chunks[:5]):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunk_type', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test 2: 해석례 (Interpretation)
    print("\n" + "=" * 60)
    print("TEST 2: Interpretation (해석례) Chunking")
    print("=" * 60)

    print(f"\nSample content ({len(SAMPLE_INTERPRETATION_CONTENT)} chars):")
    print(SAMPLE_INTERPRETATION_CONTENT[:500] + "...")

    # Test old chunker
    print("\n--- Old Strategy (InterpretationChunking) ---")
    old_chunker = InterpretationChunking()
    old_chunks = old_chunker.chunk(SAMPLE_INTERPRETATION_CONTENT, SAMPLE_INTERPRETATION_METADATA)
    print(f"Chunks: {len(old_chunks)}")
    for i, c in enumerate(old_chunks[:5]):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunking_strategy', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test new chunker
    print("\n--- New Strategy V2 (InterpretationChunkingV2) ---")
    new_chunker = InterpretationChunkingV2()
    new_chunks = new_chunker.chunk(SAMPLE_INTERPRETATION_CONTENT, SAMPLE_INTERPRETATION_METADATA)
    print(f"Chunks: {len(new_chunks)}")
    for i, c in enumerate(new_chunks[:5]):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunk_type', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test 3: 판결문 (Precedent)
    print("\n" + "=" * 60)
    print("TEST 3: Precedent (판결문) Chunking")
    print("=" * 60)

    print(f"\nSample content ({len(SAMPLE_PRECEDENT_CONTENT)} chars):")
    print(SAMPLE_PRECEDENT_CONTENT[:400] + "...")

    # Test old chunker
    print("\n--- Old Strategy (PrecedentAutoChunking) ---")
    old_chunker = PrecedentAutoChunking()
    old_chunks = old_chunker.chunk(SAMPLE_PRECEDENT_CONTENT, SAMPLE_PRECEDENT_METADATA)
    print(f"Chunks: {len(old_chunks)}")
    for i, c in enumerate(old_chunks[:5]):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunking_strategy', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test new chunker
    print("\n--- New Strategy V2 (PrecedentChunkingV2) ---")
    new_chunker = PrecedentChunkingV2()
    new_chunks = new_chunker.chunk(SAMPLE_PRECEDENT_CONTENT, SAMPLE_PRECEDENT_METADATA)
    print(f"Chunks: {len(new_chunks)}")
    for i, c in enumerate(new_chunks[:5]):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunk_type', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test 4: QA Data
    print("\n" + "=" * 60)
    print("TEST 4: QA Data Chunking")
    print("=" * 60)

    print(f"\nSample content ({len(SAMPLE_QA_CONTENT)} chars):")
    print(SAMPLE_QA_CONTENT[:400] + "...")

    # Test old chunker
    print("\n--- Old Strategy (QAPreserveChunking) ---")
    old_chunker = QAPreserveChunking()
    old_chunks = old_chunker.chunk(SAMPLE_QA_CONTENT, SAMPLE_QA_METADATA)
    print(f"Chunks: {len(old_chunks)}")
    for i, c in enumerate(old_chunks):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunk_type', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test new chunker
    print("\n--- New Strategy V2 (QAPreserveChunkingV2) ---")
    new_chunker = QAPreserveChunkingV2()
    new_chunks = new_chunker.chunk(SAMPLE_QA_CONTENT, SAMPLE_QA_METADATA)
    print(f"Chunks: {len(new_chunks)}")
    for i, c in enumerate(new_chunks):
        content_preview = c['content'][:80].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunk_type', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test 5: Long Content (Force Split)
    print("\n" + "=" * 60)
    print("TEST 5: Long Content (Force Split Test)")
    print("=" * 60)

    print(f"\nLong content ({len(SAMPLE_LONG_CONTENT)} chars):")
    print("Testing chunking of longer document...")

    long_metadata = {
        'law_id': '250',
        'article_num': '제250조',
        'article_title': '살인',
        'law_title': '형법',
        'has_structure': True,
        'type': 'source_법령'
    }

    # Test with chunk_size=300 to force splitting
    print("\n--- LegalArticleChunkingV2 (chunk_size=300) ---")
    chunker = LegalArticleChunkingV2(chunk_size=300, max_chunk_size=400)
    chunks = chunker.chunk(SAMPLE_LONG_CONTENT, long_metadata)
    print(f"Chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        content_preview = c['content'][:60].replace('\n', ' ')
        print(f"  [{i}] {len(c['content'])} chars - {c['metadata'].get('chunk_type', 'N/A')}")
        print(f"      Preview: {content_preview}...")

    # Test 6: Automatic Strategy Selection
    print("\n" + "=" * 60)
    print("TEST 6: Automatic Strategy Selection (get_chunker_v2)")
    print("=" * 60)

    test_types = [
        'source_법령',
        'source_판결문',
        'source_결정례',
        'source_해석례',
        'labeled_법령_QA',
        'labeled_판결문_QA',
        'labeled_판결문_SUM',
    ]

    for doc_type in test_types:
        chunker = get_chunker_v2(doc_type)
        print(f"  {doc_type:25s} -> {chunker.__class__.__name__}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    test_chunking_strategies()

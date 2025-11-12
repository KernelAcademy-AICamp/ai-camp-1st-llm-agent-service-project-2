#!/usr/bin/env python3
"""
LawLaw 전체 아키텍처 다이어그램 생성 스크립트
5개의 가로형 다이어그램 PNG 파일 생성
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 출력 디렉토리
OUTPUT_DIR = '/Users/jaehyungpark/Documents/libraries/lawlaw/docs/architecture'

# 색상 정의
COLORS = {
    'user': '#E8EAF6',
    'frontend': '#BBDEFB',
    'backend': '#C5E1A5',
    'db': '#FFE082',
    'ai': '#FFCCBC',
    'arrow': '#757575',
    'success': '#4CAF50',
    'warning': '#FF9800',
    'info': '#2196F3'
}

# 텍스트 스타일
FONTS = {
    'title': {'size': 18, 'weight': 'bold', 'color': '#212121'},
    'box': {'size': 14, 'weight': 'bold', 'color': '#212121'},
    'label': {'size': 11, 'color': '#424242'},
    'sub': {'size': 10, 'color': '#616161'},
    'metric': {'size': 9, 'color': '#2E7D32', 'weight': 'bold'}
}


# ============================================
# 1. Hybrid Search 구성도
# ============================================
def generate_hybrid_search_diagram():
    fig, ax = plt.subplots(figsize=(20, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 95, 'Hybrid Search 구성도 (핵심 차별점)', ha='center', va='center', **FONTS['title'])

    # 1. User Query
    box1 = FancyBboxPatch((5, 70), 12, 15, boxstyle="round,pad=0.5",
                          edgecolor='#5E35B1', facecolor=COLORS['user'], linewidth=2.5)
    ax.add_patch(box1)
    ax.text(11, 80, 'User Query', ha='center', va='center', **FONTS['box'])
    ax.text(11, 75, '"음주운전', ha='center', va='center', **FONTS['sub'])
    ax.text(11, 72, '양형 기준"', ha='center', va='center', **FONTS['sub'])

    # 2. Hybrid Retriever
    box2 = FancyBboxPatch((23, 65), 14, 25, boxstyle="round,pad=0.5",
                          edgecolor='#1976D2', facecolor=COLORS['frontend'], linewidth=2.5)
    ax.add_patch(box2)
    ax.text(30, 83, 'Hybrid', ha='center', va='center', **FONTS['box'])
    ax.text(30, 79, 'Retriever', ha='center', va='center', **FONTS['box'])
    ax.text(30, 74, 'Adaptive', ha='center', va='center', **FONTS['sub'])
    ax.text(30, 70, 'Weighting', ha='center', va='center', **FONTS['sub'])

    # 3. Semantic Search
    box3 = FancyBboxPatch((42, 70), 12, 20, boxstyle="round,pad=0.5",
                          edgecolor='#388E3C', facecolor=COLORS['backend'], linewidth=2.5)
    ax.add_patch(box3)
    ax.text(48, 84, 'Semantic', ha='center', va='center', **FONTS['box'])
    ax.text(48, 80, 'Search', ha='center', va='center', **FONTS['box'])
    ax.text(48, 76, 'ko-sroberta', ha='center', va='center', **FONTS['sub'])
    ax.text(48, 72, 'Top-15', ha='center', va='center', **FONTS['sub'])

    # 4. BM25 Search
    box4 = FancyBboxPatch((42, 40), 12, 20, boxstyle="round,pad=0.5",
                          edgecolor='#F57C00', facecolor=COLORS['db'], linewidth=2.5)
    ax.add_patch(box4)
    ax.text(48, 54, 'BM25', ha='center', va='center', **FONTS['box'])
    ax.text(48, 50, 'Keyword', ha='center', va='center', **FONTS['box'])
    ax.text(48, 46, 'TF-IDF', ha='center', va='center', **FONTS['sub'])
    ax.text(48, 42, 'Top-15', ha='center', va='center', **FONTS['sub'])

    # 5. RRF Fusion
    box5 = FancyBboxPatch((60, 50), 14, 30, boxstyle="round,pad=0.5",
                          edgecolor='#C62828', facecolor='#FFCCBC', linewidth=2.5)
    ax.add_patch(box5)
    ax.text(67, 72, 'RRF Fusion', ha='center', va='center', **FONTS['box'])
    ax.text(67, 68, 'k = 60', ha='center', va='center', **FONTS['sub'])
    ax.text(67, 63, '조항: BM25 80%', ha='center', va='center', **FONTS['sub'])
    ax.text(67, 59, '의미: Semantic 70%', ha='center', va='center', **FONTS['sub'])
    ax.text(67, 54, 'Top-5 Documents', ha='center', va='center', **FONTS['metric'])

    # 6. GPT-4
    box6 = FancyBboxPatch((80, 65), 12, 20, boxstyle="round,pad=0.5",
                          edgecolor='#E64A19', facecolor=COLORS['ai'], linewidth=2.5)
    ax.add_patch(box6)
    ax.text(86, 79, 'GPT-4', ha='center', va='center', **FONTS['box'])
    ax.text(86, 75, 'Answer', ha='center', va='center', **FONTS['box'])
    ax.text(86, 71, '+ Sources', ha='center', va='center', **FONTS['sub'])
    ax.text(86, 67, '+ 면책조항', ha='center', va='center', **FONTS['sub'])

    # 화살표
    arrows = [
        ((17, 77.5), (23, 77.5), 'Query'),
        ((37, 77.5), (42, 80), None),
        ((37, 77.5), (42, 50), None),
        ((54, 80), (60, 70), None),
        ((54, 50), (60, 60), None),
        ((74, 75), (80, 75), 'Context')
    ]

    for start, end, label in arrows:
        arrow = FancyArrowPatch(start, end, arrowstyle='->,head_width=0.6,head_length=0.8',
                               color=COLORS['arrow'], linewidth=2.5, zorder=1)
        ax.add_patch(arrow)
        if label:
            mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            ax.text(mid_x, mid_y + 2, label, ha='center', va='bottom', **FONTS['label'])

    # 성능 지표
    perf_y = 15
    ax.text(50, perf_y + 10, '성능 개선 지표', ha='center', va='center', **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})
    ax.text(20, perf_y, 'Semantic Only: 65%', ha='center', va='center', **FONTS['sub'])
    ax.text(40, perf_y, 'BM25 Only: 70%', ha='center', va='center', **FONTS['sub'])
    ax.text(60, perf_y, '→', ha='center', va='center', **{'size': 16, 'weight': 'bold', 'color': '#388E3C'})
    ax.text(80, perf_y, 'Hybrid Search: 90% (+25%)', ha='center', va='center', **FONTS['metric'])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/hybrid_search_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 1/5: Hybrid Search 다이어그램 생성 완료")


# ============================================
# 2. 데이터 레이어 구성도
# ============================================
def generate_data_layer_diagram():
    fig, ax = plt.subplots(figsize=(20, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 95, '데이터 레이어 구성도', ha='center', va='center', **FONTS['title'])

    # 1. ChromaDB
    box1 = FancyBboxPatch((10, 55), 18, 25, boxstyle="round,pad=0.5",
                          edgecolor='#F57C00', facecolor=COLORS['db'], linewidth=2.5)
    ax.add_patch(box1)
    ax.text(19, 73, 'ChromaDB', ha='center', va='center', **FONTS['box'])
    ax.text(19, 69, '388,767 docs', ha='center', va='center', **FONTS['sub'])
    ax.text(19, 64, '판례: 37만', ha='center', va='center', **FONTS['sub'])
    ax.text(19, 60, '법령: 9천', ha='center', va='center', **FONTS['sub'])
    ax.text(19, 56, '해석례: 800', ha='center', va='center', **FONTS['sub'])

    # 2. PostgreSQL
    box2 = FancyBboxPatch((35, 55), 18, 25, boxstyle="round,pad=0.5",
                          edgecolor='#0277BD', facecolor='#B3E5FC', linewidth=2.5)
    ax.add_patch(box2)
    ax.text(44, 73, 'PostgreSQL', ha='center', va='center', **FONTS['box'])
    ax.text(44, 69, 'Feedback DB', ha='center', va='center', **FONTS['sub'])
    ax.text(44, 64, '좋아요/싫어요', ha='center', va='center', **FONTS['sub'])
    ax.text(44, 60, '세션 추적', ha='center', va='center', **FONTS['sub'])
    ax.text(44, 56, 'Learning to Rank', ha='center', va='center', **FONTS['sub'])

    # 3. OpenLaw API
    box3 = FancyBboxPatch((60, 55), 18, 25, boxstyle="round,pad=0.5",
                          edgecolor='#388E3C', facecolor=COLORS['backend'], linewidth=2.5)
    ax.add_patch(box3)
    ax.text(69, 73, 'OpenLaw API', ha='center', va='center', **FONTS['box'])
    ax.text(69, 69, '판례 크롤링', ha='center', va='center', **FONTS['sub'])
    ax.text(69, 64, '일일: 10건', ha='center', va='center', **FONTS['sub'])
    ax.text(69, 60, '주간: 키워드별', ha='center', va='center', **FONTS['sub'])
    ax.text(69, 56, '증분 인덱싱', ha='center', va='center', **FONTS['sub'])

    # 4. FastAPI Backend (중앙)
    box4 = FancyBboxPatch((35, 20), 30, 18, boxstyle="round,pad=0.5",
                          edgecolor='#1976D2', facecolor=COLORS['frontend'], linewidth=2.5)
    ax.add_patch(box4)
    ax.text(50, 32, 'FastAPI Backend', ha='center', va='center', **FONTS['box'])
    ax.text(50, 28, '검색 API', ha='center', va='center', **FONTS['sub'])
    ax.text(50, 24, '피드백 수집', ha='center', va='center', **FONTS['sub'])
    ax.text(50, 21, '크롤링 스케줄', ha='center', va='center', **FONTS['sub'])

    # 화살표 (양방향)
    arrows = [
        ((19, 55), (44, 38), '벡터 검색'),
        ((44, 55), (50, 38), '피드백'),
        ((69, 55), (56, 38), '크롤링')
    ]

    for start, end, label in arrows:
        arrow = FancyArrowPatch(start, end, arrowstyle='<->,head_width=0.6,head_length=0.8',
                               color=COLORS['arrow'], linewidth=2.5, zorder=1)
        ax.add_patch(arrow)
        mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        ax.text(mid_x, mid_y + 2, label, ha='center', va='bottom', **FONTS['label'])

    # 데이터 확장 로드맵
    roadmap_y = 8
    ax.text(50, roadmap_y + 5, '데이터 확장 로드맵', ha='center', va='center', **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})
    ax.text(15, roadmap_y, '현재: 388K', ha='center', va='center', **FONTS['sub'])
    ax.text(35, roadmap_y, '→ Phase 1.5: +월 300건', ha='center', va='center', **FONTS['sub'])
    ax.text(55, roadmap_y, '→ Phase 2: +85K', ha='center', va='center', **FONTS['sub'])
    ax.text(75, roadmap_y, '목표: 120K+ 문서', ha='center', va='center', **FONTS['metric'])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/data_layer_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 2/5: 데이터 레이어 다이어그램 생성 완료")


# ============================================
# 3. Constitutional AI 파이프라인
# ============================================
def generate_constitutional_ai_diagram():
    fig, ax = plt.subplots(figsize=(20, 9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 95, 'Constitutional AI 파이프라인', ha='center', va='center', **FONTS['title'])

    # 단계별 박스
    stages = [
        (5, 60, 'RAG 검색', ['Hybrid Search', 'Top-5 판례/법령'], '#BBDEFB', '#1976D2'),
        (20, 60, '프롬프트 구성', ['User Query', '+ Context'], '#C5E1A5', '#388E3C'),
        (35, 60, 'GPT-4 초기답변', ['Constitutional AI', '6가지 원칙'], '#FFE082', '#F57C00'),
        (50, 60, 'Self-Critique', ['출처 명시?', '환각 없음?'], '#FFCCBC', '#E64A19'),
        (65, 60, '수정된 답변', ['검증 완료', '최종 답변'], '#C5E1A5', '#388E3C'),
        (80, 60, 'Frontend 표시', ['답변 + 출처', '신뢰도 점수'], '#BBDEFB', '#1976D2')
    ]

    for i, (x, y, title, items, facecolor, edgecolor) in enumerate(stages):
        box = FancyBboxPatch((x, y), 12, 20, boxstyle="round,pad=0.5",
                            edgecolor=edgecolor, facecolor=facecolor, linewidth=2.5)
        ax.add_patch(box)
        ax.text(x + 6, y + 16, title, ha='center', va='center', **FONTS['box'])
        ax.text(x + 6, y + 12, items[0], ha='center', va='center', **FONTS['sub'])
        ax.text(x + 6, y + 9, items[1], ha='center', va='center', **FONTS['sub'])

        # 화살표 (마지막 제외)
        if i < len(stages) - 1:
            arrow = FancyArrowPatch((x + 12, y + 10), (x + 15, y + 10),
                                   arrowstyle='->,head_width=0.6,head_length=0.8',
                                   color=COLORS['arrow'], linewidth=2.5, zorder=1)
            ax.add_patch(arrow)

    # 6가지 원칙 박스
    principles_y = 35
    ax.text(50, principles_y + 10, 'Constitutional AI 6가지 원칙', ha='center', va='center',
           **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})

    principles = [
        '✅ 1. 판례 기반만 답변',
        '✅ 2. 모든 주장에 출처 명시',
        '✅ 3. 환각 방지 (검색 문서 기반)',
        '✅ 4. 전문적 어조',
        '✅ 5. 면책 조항 포함',
        '✅ 6. 법률 용어 정확성'
    ]

    for i, principle in enumerate(principles):
        col = i % 3
        row = i // 3
        x = 20 + col * 22
        y = principles_y - row * 5
        ax.text(x, y, principle, ha='left', va='center', **FONTS['sub'])

    # 성능 지표
    perf_y = 8
    ax.text(50, perf_y + 5, '검증된 성능', ha='center', va='center', **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})
    ax.text(20, perf_y, '환각 감소: 70%', ha='center', va='center', **FONTS['metric'])
    ax.text(45, perf_y, '출처 명시율: 95%+', ha='center', va='center', **FONTS['metric'])
    ax.text(70, perf_y, '답변 품질: 4.2/5.0', ha='center', va='center', **FONTS['metric'])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/constitutional_ai_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 3/5: Constitutional AI 다이어그램 생성 완료")


# ============================================
# 4. AI/ML 파이프라인
# ============================================
def generate_ai_ml_pipeline_diagram():
    fig, ax = plt.subplots(figsize=(20, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 95, 'AI/ML 처리 파이프라인', ha='center', va='center', **FONTS['title'])

    # 단계별 박스
    stages = [
        (5, 60, '문서 입력', ['PDF/DOCX', 'TXT'], '#E8EAF6', '#5E35B1'),
        (18, 60, 'FileParser', ['Text', 'Extraction'], '#BBDEFB', '#1976D2'),
        (31, 60, 'Embedder', ['ko-sroberta', '768-dim'], '#C5E1A5', '#388E3C'),
        (44, 60, 'ChromaDB', ['388,767', 'documents'], '#FFE082', '#F57C00'),
        (57, 60, 'Hybrid', ['Retriever', 'Top-5'], '#FFCCBC', '#E64A19'),
        (70, 60, 'Constitutional', ['AI', 'GPT-4'], '#B3E5FC', '#0277BD'),
        (83, 60, 'Answer', ['+ Sources', '+ 면책'], '#C5E1A5', '#388E3C')
    ]

    for i, (x, y, title, items, facecolor, edgecolor) in enumerate(stages):
        box = FancyBboxPatch((x, y), 10, 18, boxstyle="round,pad=0.5",
                            edgecolor=edgecolor, facecolor=facecolor, linewidth=2.5)
        ax.add_patch(box)
        ax.text(x + 5, y + 14, title, ha='center', va='center', **FONTS['box'])
        ax.text(x + 5, y + 10, items[0], ha='center', va='center', **FONTS['sub'])
        ax.text(x + 5, y + 7, items[1], ha='center', va='center', **FONTS['sub'])

        # 화살표
        if i < len(stages) - 1:
            arrow = FancyArrowPatch((x + 10, y + 9), (x + 13, y + 9),
                                   arrowstyle='->,head_width=0.6,head_length=0.8',
                                   color=COLORS['arrow'], linewidth=2.5, zorder=1)
            ax.add_patch(arrow)

    # 처리 시간
    times_y = 40
    ax.text(50, times_y + 8, '처리 시간 (평균)', ha='center', va='center', **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})
    ax.text(15, times_y, 'Parsing: < 1초', ha='center', va='center', **FONTS['sub'])
    ax.text(35, times_y, 'Embedding: < 0.5초', ha='center', va='center', **FONTS['sub'])
    ax.text(55, times_y, 'Search: 0.8초', ha='center', va='center', **FONTS['sub'])
    ax.text(75, times_y, 'GPT-4: 3-5초', ha='center', va='center', **FONTS['sub'])

    # 성능 지표
    perf_y = 20
    ax.text(50, perf_y + 8, '성능 지표', ha='center', va='center', **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})
    ax.text(20, perf_y, '검색 정확도: 90%', ha='center', va='center', **FONTS['metric'])
    ax.text(45, perf_y, '메모리: ~1.5GB', ha='center', va='center', **FONTS['metric'])
    ax.text(70, perf_y, '전체 응답: 5-10초', ha='center', va='center', **FONTS['metric'])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/ai_ml_pipeline_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 4/5: AI/ML 파이프라인 다이어그램 생성 완료")


# ============================================
# 5. 데이터베이스 스키마
# ============================================
def generate_database_schema_diagram():
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 95, '데이터베이스 스키마 (4개 테이블)', ha='center', va='center', **FONTS['title'])

    # 1. Users 테이블
    box1_y = 60
    box1 = FancyBboxPatch((5, box1_y), 20, 25, boxstyle="round,pad=0.5",
                          edgecolor='#1976D2', facecolor=COLORS['frontend'], linewidth=2.5)
    ax.add_patch(box1)
    ax.text(15, box1_y + 22, 'Users (사용자)', ha='center', va='center', **FONTS['box'])

    users_fields = [
        'id (UUID, PK)',
        'email',
        'hashed_password',
        'full_name',
        'lawyer_registration_number',
        'specializations (JSON)',
        'is_active',
        'created_at'
    ]
    for i, field in enumerate(users_fields):
        ax.text(15, box1_y + 18 - i * 2.2, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 2. Precedents 테이블
    box2_y = 60
    box2 = FancyBboxPatch((28, box2_y), 20, 25, boxstyle="round,pad=0.5",
                          edgecolor='#388E3C', facecolor=COLORS['backend'], linewidth=2.5)
    ax.add_patch(box2)
    ax.text(38, box2_y + 22, 'Precedents (판례)', ha='center', va='center', **FONTS['box'])

    precedents_fields = [
        'id (UUID, PK)',
        'case_number (UNIQUE)',
        'title',
        'summary',
        'full_text',
        'reference_statutes (JSON)',
        'decision_date',
        'case_type'
    ]
    for i, field in enumerate(precedents_fields):
        ax.text(38, box2_y + 18 - i * 2.2, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 3. PrecedentFeedback 테이블
    box3_y = 60
    box3 = FancyBboxPatch((51, box3_y), 20, 25, boxstyle="round,pad=0.5",
                          edgecolor='#F57C00', facecolor=COLORS['db'], linewidth=2.5)
    ax.add_patch(box3)
    ax.text(61, box3_y + 22, 'PrecedentFeedback', ha='center', va='center', **FONTS['box'])

    feedback_fields = [
        'id (UUID, PK)',
        'precedent_id',
        'user_id (FK → Users)',
        'query',
        'feedback_type',
        'is_helpful',
        'relevance_score',
        'session_id'
    ]
    for i, field in enumerate(feedback_fields):
        ax.text(61, box3_y + 18 - i * 2.2, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 4. PrecedentFeedbackStats 테이블
    box4_y = 60
    box4 = FancyBboxPatch((74, box4_y), 20, 25, boxstyle="round,pad=0.5",
                          edgecolor='#E64A19', facecolor=COLORS['ai'], linewidth=2.5)
    ax.add_patch(box4)
    ax.text(84, box4_y + 22, 'FeedbackStats (집계)', ha='center', va='center', **FONTS['box'])

    stats_fields = [
        'precedent_id (PK)',
        'total_likes',
        'total_dislikes',
        'like_ratio',
        'total_feedback_count',
        'avg_relevance_score',
        'should_exclude',
        'last_updated'
    ]
    for i, field in enumerate(stats_fields):
        ax.text(84, box4_y + 18 - i * 2.2, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 관계 화살표
    # Users → Feedback
    arrow1 = FancyArrowPatch((25, box3_y + 15), (51, box3_y + 15),
                            arrowstyle='->,head_width=0.4,head_length=0.6',
                            color='#0277BD', linewidth=2, linestyle='--', zorder=1)
    ax.add_patch(arrow1)
    ax.text(38, box3_y + 17, 'user_id (FK)', ha='center', va='bottom', **{'size': 9, 'color': '#0277BD'})

    # Feedback → Stats
    arrow2 = FancyArrowPatch((71, box3_y + 10), (74, box4_y + 10),
                            arrowstyle='->,head_width=0.4,head_length=0.6',
                            color='#F57C00', linewidth=2, linestyle='--', zorder=1)
    ax.add_patch(arrow2)
    ax.text(72.5, box3_y + 12, '집계', ha='center', va='bottom', **{'size': 9, 'color': '#F57C00'})

    # 설명
    desc_y = 25
    ax.text(50, desc_y + 8, 'DB 타입 및 용도', ha='center', va='center', **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})
    ax.text(15, desc_y, 'SQLite (개발)', ha='center', va='center', **FONTS['sub'])
    ax.text(35, desc_y, 'PostgreSQL (프로덕션)', ha='center', va='center', **FONTS['sub'])
    ax.text(55, desc_y, '파일: lawlaw.db (124KB)', ha='center', va='center', **FONTS['sub'])
    ax.text(75, desc_y, '위치: data/lawlaw.db', ha='center', va='center', **FONTS['sub'])

    # 활용
    use_y = 15
    ax.text(50, use_y + 5, '활용 시나리오', ha='center', va='center', **{'size': 14, 'weight': 'bold', 'color': '#1B5E20'})
    ax.text(20, use_y, '1) 사용자 인증', ha='center', va='center', **FONTS['sub'])
    ax.text(40, use_y, '2) 판례 메타데이터', ha='center', va='center', **FONTS['sub'])
    ax.text(60, use_y, '3) 피드백 수집', ha='center', va='center', **FONTS['sub'])
    ax.text(80, use_y, '4) Learning to Rank', ha='center', va='center', **FONTS['metric'])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/database_schema_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 5/5: 데이터베이스 스키마 다이어그램 생성 완료")


# ============================================
# 메인 실행
# ============================================
if __name__ == "__main__":
    print("🎨 LawLaw 아키텍처 다이어그램 생성 시작...\n")

    # 출력 디렉토리 확인
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 각 다이어그램 생성
    generate_hybrid_search_diagram()
    generate_data_layer_diagram()
    generate_constitutional_ai_diagram()
    generate_ai_ml_pipeline_diagram()
    generate_database_schema_diagram()

    print(f"\n🎉 모든 다이어그램 생성 완료!")
    print(f"📁 저장 위치: {OUTPUT_DIR}")
    print(f"\n생성된 파일:")
    print(f"  1. hybrid_search_diagram.png")
    print(f"  2. data_layer_diagram.png")
    print(f"  3. constitutional_ai_diagram.png")
    print(f"  4. ai_ml_pipeline_diagram.png")
    print(f"  5. database_schema_diagram.png")
    print(f"\n✨ 고해상도 PNG (300 DPI), GitHub/문서에 바로 사용 가능!")

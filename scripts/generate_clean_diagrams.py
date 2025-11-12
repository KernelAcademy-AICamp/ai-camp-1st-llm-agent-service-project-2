#!/usr/bin/env python3
"""
LawLaw 아키텍처 다이어그램 생성 (간결 버전)
하단 텍스트 없이 다이어그램만 깔끔하게 생성
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = '/Users/jaehyungpark/Documents/libraries/lawlaw/docs/architecture'

# 색상 정의
COLORS = {
    'user': '#E8EAF6',
    'frontend': '#BBDEFB',
    'backend': '#C5E1A5',
    'db': '#FFE082',
    'ai': '#FFCCBC',
    'arrow': '#757575',
}

# 텍스트 스타일
FONTS = {
    'title': {'size': 18, 'weight': 'bold', 'color': '#212121'},
    'box': {'size': 14, 'weight': 'bold', 'color': '#212121'},
    'label': {'size': 11, 'color': '#424242'},
    'sub': {'size': 10, 'color': '#616161'},
}


# ============================================
# 1. Hybrid Search 구성도 (간결)
# ============================================
def generate_hybrid_search_clean():
    fig, ax = plt.subplots(figsize=(20, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 92, 'Hybrid Search 구성도', ha='center', va='center', **FONTS['title'])

    # 1. User Query
    box1 = FancyBboxPatch((5, 60), 12, 18, boxstyle="round,pad=0.5",
                          edgecolor='#5E35B1', facecolor=COLORS['user'], linewidth=2.5)
    ax.add_patch(box1)
    ax.text(11, 72, 'User Query', ha='center', va='center', **FONTS['box'])
    ax.text(11, 67, '"음주운전', ha='center', va='center', **FONTS['sub'])
    ax.text(11, 63, '양형 기준"', ha='center', va='center', **FONTS['sub'])

    # 2. Hybrid Retriever
    box2 = FancyBboxPatch((23, 55), 14, 28, boxstyle="round,pad=0.5",
                          edgecolor='#1976D2', facecolor=COLORS['frontend'], linewidth=2.5)
    ax.add_patch(box2)
    ax.text(30, 76, 'Hybrid', ha='center', va='center', **FONTS['box'])
    ax.text(30, 71, 'Retriever', ha='center', va='center', **FONTS['box'])
    ax.text(30, 66, 'Adaptive', ha='center', va='center', **FONTS['sub'])
    ax.text(30, 61, 'Weighting', ha='center', va='center', **FONTS['sub'])

    # 3. Semantic Search
    box3 = FancyBboxPatch((42, 65), 12, 23, boxstyle="round,pad=0.5",
                          edgecolor='#388E3C', facecolor=COLORS['backend'], linewidth=2.5)
    ax.add_patch(box3)
    ax.text(48, 81, 'Semantic', ha='center', va='center', **FONTS['box'])
    ax.text(48, 76, 'Search', ha='center', va='center', **FONTS['box'])
    ax.text(48, 72, 'ko-sroberta', ha='center', va='center', **FONTS['sub'])
    ax.text(48, 68, 'Top-15', ha='center', va='center', **FONTS['sub'])

    # 4. BM25 Search
    box4 = FancyBboxPatch((42, 35), 12, 23, boxstyle="round,pad=0.5",
                          edgecolor='#F57C00', facecolor=COLORS['db'], linewidth=2.5)
    ax.add_patch(box4)
    ax.text(48, 51, 'BM25', ha='center', va='center', **FONTS['box'])
    ax.text(48, 46, 'Keyword', ha='center', va='center', **FONTS['box'])
    ax.text(48, 42, 'TF-IDF', ha='center', va='center', **FONTS['sub'])
    ax.text(48, 38, 'Top-15', ha='center', va='center', **FONTS['sub'])

    # 5. RRF Fusion
    box5 = FancyBboxPatch((60, 45), 14, 33, boxstyle="round,pad=0.5",
                          edgecolor='#C62828', facecolor='#FFCCBC', linewidth=2.5)
    ax.add_patch(box5)
    ax.text(67, 71, 'RRF Fusion', ha='center', va='center', **FONTS['box'])
    ax.text(67, 67, 'k = 60', ha='center', va='center', **FONTS['sub'])
    ax.text(67, 62, '조항: BM25 80%', ha='center', va='center', **FONTS['sub'])
    ax.text(67, 57, '의미: Semantic 70%', ha='center', va='center', **FONTS['sub'])
    ax.text(67, 51, 'Top-5 Documents', ha='center', va='center', **{'size': 11, 'weight': 'bold', 'color': '#2E7D32'})

    # 6. GPT-4
    box6 = FancyBboxPatch((80, 60), 12, 23, boxstyle="round,pad=0.5",
                          edgecolor='#E64A19', facecolor=COLORS['ai'], linewidth=2.5)
    ax.add_patch(box6)
    ax.text(86, 76, 'GPT-4', ha='center', va='center', **FONTS['box'])
    ax.text(86, 71, 'Answer', ha='center', va='center', **FONTS['box'])
    ax.text(86, 67, '+ Sources', ha='center', va='center', **FONTS['sub'])
    ax.text(86, 63, '+ 면책조항', ha='center', va='center', **FONTS['sub'])

    # 화살표
    arrows = [
        ((17, 69), (23, 69), 'Query'),
        ((37, 72), (42, 76), None),
        ((37, 66), (42, 46), None),
        ((54, 76), (60, 68), None),
        ((54, 46), (60, 58), None),
        ((74, 71.5), (80, 71.5), 'Context')
    ]

    for start, end, label in arrows:
        arrow = FancyArrowPatch(start, end, arrowstyle='->,head_width=0.6,head_length=0.8',
                               color=COLORS['arrow'], linewidth=2.5, zorder=1)
        ax.add_patch(arrow)
        if label:
            mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            ax.text(mid_x, mid_y + 2, label, ha='center', va='bottom', **FONTS['label'])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/hybrid_search_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 1/5: Hybrid Search 다이어그램 생성 완료")


# ============================================
# 2. 데이터 레이어 구성도 (간결)
# ============================================
def generate_data_layer_clean():
    fig, ax = plt.subplots(figsize=(20, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 92, '데이터 레이어 구성도', ha='center', va='center', **FONTS['title'])

    # 1. ChromaDB
    box1 = FancyBboxPatch((10, 48), 18, 28, boxstyle="round,pad=0.5",
                          edgecolor='#F57C00', facecolor=COLORS['db'], linewidth=2.5)
    ax.add_patch(box1)
    ax.text(19, 69, 'ChromaDB', ha='center', va='center', **FONTS['box'])
    ax.text(19, 64, '388,767 docs', ha='center', va='center', **FONTS['sub'])
    ax.text(19, 59, '판례: 37만', ha='center', va='center', **FONTS['sub'])
    ax.text(19, 54, '법령: 9천', ha='center', va='center', **FONTS['sub'])
    ax.text(19, 50, '해석례: 800', ha='center', va='center', **FONTS['sub'])

    # 2. PostgreSQL
    box2 = FancyBboxPatch((35, 48), 18, 28, boxstyle="round,pad=0.5",
                          edgecolor='#0277BD', facecolor='#B3E5FC', linewidth=2.5)
    ax.add_patch(box2)
    ax.text(44, 69, 'PostgreSQL', ha='center', va='center', **FONTS['box'])
    ax.text(44, 64, 'Feedback DB', ha='center', va='center', **FONTS['sub'])
    ax.text(44, 59, '좋아요/싫어요', ha='center', va='center', **FONTS['sub'])
    ax.text(44, 54, '세션 추적', ha='center', va='center', **FONTS['sub'])
    ax.text(44, 50, 'LTR 학습 데이터', ha='center', va='center', **FONTS['sub'])

    # 3. OpenLaw API
    box3 = FancyBboxPatch((60, 48), 18, 28, boxstyle="round,pad=0.5",
                          edgecolor='#388E3C', facecolor=COLORS['backend'], linewidth=2.5)
    ax.add_patch(box3)
    ax.text(69, 69, 'OpenLaw API', ha='center', va='center', **FONTS['box'])
    ax.text(69, 64, '판례 크롤링', ha='center', va='center', **FONTS['sub'])
    ax.text(69, 59, '일일: 10건', ha='center', va='center', **FONTS['sub'])
    ax.text(69, 54, '주간: 키워드별', ha='center', va='center', **FONTS['sub'])
    ax.text(69, 50, '증분 인덱싱', ha='center', va='center', **FONTS['sub'])

    # 4. FastAPI Backend (중앙)
    box4 = FancyBboxPatch((35, 15), 30, 20, boxstyle="round,pad=0.5",
                          edgecolor='#1976D2', facecolor=COLORS['frontend'], linewidth=2.5)
    ax.add_patch(box4)
    ax.text(50, 29, 'FastAPI Backend', ha='center', va='center', **FONTS['box'])
    ax.text(50, 25, '검색 API', ha='center', va='center', **FONTS['sub'])
    ax.text(50, 21, '피드백 수집', ha='center', va='center', **FONTS['sub'])
    ax.text(50, 17, '크롤링 스케줄', ha='center', va='center', **FONTS['sub'])

    # 화살표 (양방향)
    arrows = [
        ((19, 48), (44, 35), '벡터 검색'),
        ((44, 48), (50, 35), '피드백'),
        ((69, 48), (56, 35), '크롤링')
    ]

    for start, end, label in arrows:
        arrow = FancyArrowPatch(start, end, arrowstyle='<->,head_width=0.6,head_length=0.8',
                               color=COLORS['arrow'], linewidth=2.5, zorder=1)
        ax.add_patch(arrow)
        mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        ax.text(mid_x, mid_y + 2, label, ha='center', va='bottom', **FONTS['label'])

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/data_layer_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 2/5: 데이터 레이어 다이어그램 생성 완료")


# ============================================
# 3. Constitutional AI 파이프라인 (간결)
# ============================================
def generate_constitutional_ai_clean():
    fig, ax = plt.subplots(figsize=(20, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 92, 'Constitutional AI 파이프라인', ha='center', va='center', **FONTS['title'])

    # 단계별 박스
    stages = [
        (5, 50, 'RAG 검색', ['Hybrid Search', 'Top-5 판례'], '#BBDEFB', '#1976D2'),
        (20, 50, '프롬프트 구성', ['User Query', '+ Context'], '#C5E1A5', '#388E3C'),
        (35, 50, 'GPT-4\n초기답변', ['Constitutional AI', '6가지 원칙'], '#FFE082', '#F57C00'),
        (50, 50, 'Self-Critique', ['출처 명시?', '환각 없음?'], '#FFCCBC', '#E64A19'),
        (65, 50, '수정된 답변', ['검증 완료', '최종 답변'], '#C5E1A5', '#388E3C'),
        (80, 50, 'Frontend\n표시', ['답변 + 출처', '신뢰도 점수'], '#BBDEFB', '#1976D2')
    ]

    for i, (x, y, title, items, facecolor, edgecolor) in enumerate(stages):
        box = FancyBboxPatch((x, y), 12, 23, boxstyle="round,pad=0.5",
                            edgecolor=edgecolor, facecolor=facecolor, linewidth=2.5)
        ax.add_patch(box)
        ax.text(x + 6, y + 18, title, ha='center', va='center', **FONTS['box'])
        ax.text(x + 6, y + 14, items[0], ha='center', va='center', **FONTS['sub'])
        ax.text(x + 6, y + 10, items[1], ha='center', va='center', **FONTS['sub'])

        # 화살표
        if i < len(stages) - 1:
            arrow = FancyArrowPatch((x + 12, y + 11.5), (x + 15, y + 11.5),
                                   arrowstyle='->,head_width=0.6,head_length=0.8',
                                   color=COLORS['arrow'], linewidth=2.5, zorder=1)
            ax.add_patch(arrow)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/constitutional_ai_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 3/5: Constitutional AI 다이어그램 생성 완료")


# ============================================
# 4. AI/ML 파이프라인 (간결)
# ============================================
def generate_ai_ml_pipeline_clean():
    fig, ax = plt.subplots(figsize=(20, 7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 92, 'AI/ML 처리 파이프라인', ha='center', va='center', **FONTS['title'])

    # 단계별 박스
    stages = [
        (5, 50, '문서 입력', ['PDF/DOCX', 'TXT'], '#E8EAF6', '#5E35B1'),
        (18, 50, 'FileParser', ['Text', 'Extraction'], '#BBDEFB', '#1976D2'),
        (31, 50, 'Embedder', ['ko-sroberta', '768-dim'], '#C5E1A5', '#388E3C'),
        (44, 50, 'ChromaDB', ['388,767', 'documents'], '#FFE082', '#F57C00'),
        (57, 50, 'Hybrid\nRetriever', ['Semantic+BM25', 'Top-5'], '#FFCCBC', '#E64A19'),
        (70, 50, 'Constitutional\nAI', ['GPT-4', '6 Principles'], '#B3E5FC', '#0277BD'),
        (83, 50, 'Answer', ['+ Sources', '+ 면책'], '#C5E1A5', '#388E3C')
    ]

    for i, (x, y, title, items, facecolor, edgecolor) in enumerate(stages):
        box = FancyBboxPatch((x, y), 10, 23, boxstyle="round,pad=0.5",
                            edgecolor=edgecolor, facecolor=facecolor, linewidth=2.5)
        ax.add_patch(box)
        ax.text(x + 5, y + 18, title, ha='center', va='center', **FONTS['box'])
        ax.text(x + 5, y + 13, items[0], ha='center', va='center', **FONTS['sub'])
        ax.text(x + 5, y + 9, items[1], ha='center', va='center', **FONTS['sub'])

        # 화살표
        if i < len(stages) - 1:
            arrow = FancyArrowPatch((x + 10, y + 11.5), (x + 13, y + 11.5),
                                   arrowstyle='->,head_width=0.6,head_length=0.8',
                                   color=COLORS['arrow'], linewidth=2.5, zorder=1)
            ax.add_patch(arrow)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/ai_ml_pipeline_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 4/5: AI/ML 파이프라인 다이어그램 생성 완료")


# ============================================
# 5. 데이터베이스 스키마 (간결)
# ============================================
def generate_database_schema_clean():
    fig, ax = plt.subplots(figsize=(20, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 제목
    ax.text(50, 92, '데이터베이스 스키마', ha='center', va='center', **FONTS['title'])

    # 1. Users 테이블
    box1_y = 48
    box1 = FancyBboxPatch((5, box1_y), 20, 30, boxstyle="round,pad=0.5",
                          edgecolor='#1976D2', facecolor=COLORS['frontend'], linewidth=2.5)
    ax.add_patch(box1)
    ax.text(15, box1_y + 27, 'Users (사용자)', ha='center', va='center', **FONTS['box'])

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
        ax.text(15, box1_y + 22 - i * 2.5, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 2. Precedents 테이블
    box2_y = 48
    box2 = FancyBboxPatch((28, box2_y), 20, 30, boxstyle="round,pad=0.5",
                          edgecolor='#388E3C', facecolor=COLORS['backend'], linewidth=2.5)
    ax.add_patch(box2)
    ax.text(38, box2_y + 27, 'Precedents (판례)', ha='center', va='center', **FONTS['box'])

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
        ax.text(38, box2_y + 22 - i * 2.5, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 3. PrecedentFeedback 테이블
    box3_y = 48
    box3 = FancyBboxPatch((51, box3_y), 20, 30, boxstyle="round,pad=0.5",
                          edgecolor='#F57C00', facecolor=COLORS['db'], linewidth=2.5)
    ax.add_patch(box3)
    ax.text(61, box3_y + 27, 'PrecedentFeedback', ha='center', va='center', **FONTS['box'])

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
        ax.text(61, box3_y + 22 - i * 2.5, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 4. PrecedentFeedbackStats 테이블
    box4_y = 48
    box4 = FancyBboxPatch((74, box4_y), 20, 30, boxstyle="round,pad=0.5",
                          edgecolor='#E64A19', facecolor=COLORS['ai'], linewidth=2.5)
    ax.add_patch(box4)
    ax.text(84, box4_y + 27, 'FeedbackStats (집계)', ha='center', va='center', **FONTS['box'])

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
        ax.text(84, box4_y + 22 - i * 2.5, field, ha='center', va='center', **{'size': 9, 'color': '#424242'})

    # 관계 화살표
    # Users → Feedback
    arrow1 = FancyArrowPatch((25, box3_y + 18), (51, box3_y + 18),
                            arrowstyle='->,head_width=0.4,head_length=0.6',
                            color='#0277BD', linewidth=2, linestyle='--', zorder=1)
    ax.add_patch(arrow1)
    ax.text(38, box3_y + 20, 'user_id (FK)', ha='center', va='bottom', **{'size': 9, 'color': '#0277BD'})

    # Feedback → Stats
    arrow2 = FancyArrowPatch((71, box3_y + 13), (74, box4_y + 13),
                            arrowstyle='->,head_width=0.4,head_length=0.6',
                            color='#F57C00', linewidth=2, linestyle='--', zorder=1)
    ax.add_patch(arrow2)
    ax.text(72.5, box3_y + 15, '집계', ha='center', va='bottom', **{'size': 9, 'color': '#F57C00'})

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/database_schema_diagram.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print("✅ 5/5: 데이터베이스 스키마 다이어그램 생성 완료")


# ============================================
# 메인 실행
# ============================================
if __name__ == "__main__":
    print("🎨 LawLaw 아키텍처 다이어그램 생성 (간결 버전)...\n")

    generate_hybrid_search_clean()
    generate_data_layer_clean()
    generate_constitutional_ai_clean()
    generate_ai_ml_pipeline_clean()
    generate_database_schema_clean()

    print(f"\n🎉 모든 다이어그램 생성 완료!")
    print(f"📁 저장 위치: {OUTPUT_DIR}")
    print(f"\n생성된 파일:")
    print(f"  1. hybrid_search_diagram.png")
    print(f"  2. data_layer_diagram.png")
    print(f"  3. constitutional_ai_diagram.png")
    print(f"  4. ai_ml_pipeline_diagram.png")
    print(f"  5. database_schema_diagram.png")
    print(f"\n✨ 하단 텍스트 제거, 다이어그램만 깔끔하게!")

#!/usr/bin/env python3
"""
LawLaw 시스템 아키텍처 다이어그램 생성 스크립트
가로형 레이아웃으로 깔끔한 구성도 생성
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'  # macOS
plt.rcParams['axes.unicode_minus'] = False

# Figure 생성 (가로형)
fig, ax = plt.subplots(figsize=(20, 7))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# 색상 정의
COLOR_USER = '#E8EAF6'       # 연한 보라
COLOR_FRONTEND = '#BBDEFB'   # 연한 파랑
COLOR_BACKEND = '#C5E1A5'    # 연한 초록
COLOR_DB = '#FFE082'         # 연한 노랑
COLOR_AI = '#FFCCBC'         # 연한 주황
COLOR_ARROW = '#757575'      # 회색

# 텍스트 스타일
FONT_TITLE = {'size': 18, 'weight': 'bold', 'color': '#212121'}
FONT_BOX = {'size': 14, 'weight': 'bold', 'color': '#212121'}
FONT_LABEL = {'size': 11, 'color': '#424242'}
FONT_SUB = {'size': 10, 'color': '#616161'}

# ============================================
# 1. User (변호사)
# ============================================
box1 = FancyBboxPatch(
    (5, 70), 12, 15,
    boxstyle="round,pad=0.5",
    edgecolor='#5E35B1',
    facecolor=COLOR_USER,
    linewidth=2.5
)
ax.add_patch(box1)
ax.text(11, 80, 'User', ha='center', va='center', **FONT_BOX)
ax.text(11, 75, '(변호사)', ha='center', va='center', **FONT_SUB)

# ============================================
# 2. React Frontend
# ============================================
box2 = FancyBboxPatch(
    (25, 65), 14, 25,
    boxstyle="round,pad=0.5",
    edgecolor='#1976D2',
    facecolor=COLOR_FRONTEND,
    linewidth=2.5
)
ax.add_patch(box2)
ax.text(32, 83, 'React', ha='center', va='center', **FONT_BOX)
ax.text(32, 79, 'Frontend', ha='center', va='center', **FONT_BOX)
ax.text(32, 74, 'TypeScript', ha='center', va='center', **FONT_SUB)
ax.text(32, 70, 'Port 3000', ha='center', va='center', **FONT_SUB)

# ============================================
# 3. FastAPI Backend
# ============================================
box3 = FancyBboxPatch(
    (47, 50), 16, 40,
    boxstyle="round,pad=0.5",
    edgecolor='#388E3C',
    facecolor=COLOR_BACKEND,
    linewidth=2.5
)
ax.add_patch(box3)
ax.text(55, 83, 'FastAPI', ha='center', va='center', **FONT_BOX)
ax.text(55, 79, 'Backend', ha='center', va='center', **FONT_BOX)
ax.text(55, 74, 'Python 3.10', ha='center', va='center', **FONT_SUB)
ax.text(55, 70, 'Port 8000', ha='center', va='center', **FONT_SUB)

# Backend 내부 모듈
ax.text(55, 64, 'RAG System', ha='center', va='center', **{'size': 10, 'color': '#2E7D32'})
ax.text(55, 60, 'Hybrid Search', ha='center', va='center', **{'size': 9, 'color': '#558B2F'})
ax.text(55, 56, 'Constitutional AI', ha='center', va='center', **{'size': 9, 'color': '#558B2F'})

# ============================================
# 4. ChromaDB (왼쪽 아래)
# ============================================
box4 = FancyBboxPatch(
    (42, 10), 14, 18,
    boxstyle="round,pad=0.5",
    edgecolor='#F57C00',
    facecolor=COLOR_DB,
    linewidth=2.5
)
ax.add_patch(box4)
ax.text(49, 23, 'ChromaDB', ha='center', va='center', **FONT_BOX)
ax.text(49, 19, '388K docs', ha='center', va='center', **FONT_SUB)
ax.text(49, 15, 'Vector Search', ha='center', va='center', **FONT_SUB)

# ============================================
# 5. GPT-4 Turbo (오른쪽)
# ============================================
box5 = FancyBboxPatch(
    (71, 65), 14, 25,
    boxstyle="round,pad=0.5",
    edgecolor='#E64A19',
    facecolor=COLOR_AI,
    linewidth=2.5
)
ax.add_patch(box5)
ax.text(78, 83, 'GPT-4', ha='center', va='center', **FONT_BOX)
ax.text(78, 79, 'Turbo', ha='center', va='center', **FONT_BOX)
ax.text(78, 74, 'OpenAI API', ha='center', va='center', **FONT_SUB)
ax.text(78, 70, 'Constitutional AI', ha='center', va='center', **FONT_SUB)

# ============================================
# 6. PostgreSQL (오른쪽 아래)
# ============================================
box6 = FancyBboxPatch(
    (68, 10), 14, 18,
    boxstyle="round,pad=0.5",
    edgecolor='#0277BD',
    facecolor='#B3E5FC',
    linewidth=2.5
)
ax.add_patch(box6)
ax.text(75, 23, 'PostgreSQL', ha='center', va='center', **FONT_BOX)
ax.text(75, 19, 'Feedback DB', ha='center', va='center', **FONT_SUB)
ax.text(75, 15, 'User Ratings', ha='center', va='center', **FONT_SUB)

# ============================================
# 화살표 그리기
# ============================================

# 1. User → Frontend
arrow1 = FancyArrowPatch(
    (17, 77.5), (25, 77.5),
    arrowstyle='->,head_width=0.6,head_length=0.8',
    color=COLOR_ARROW,
    linewidth=2.5,
    zorder=1
)
ax.add_patch(arrow1)
ax.text(21, 79.5, 'Query', ha='center', va='bottom', **FONT_LABEL)

# 2. Frontend → Backend
arrow2 = FancyArrowPatch(
    (39, 77.5), (47, 77.5),
    arrowstyle='->,head_width=0.6,head_length=0.8',
    color=COLOR_ARROW,
    linewidth=2.5,
    zorder=1
)
ax.add_patch(arrow2)
ax.text(43, 79.5, 'REST API', ha='center', va='bottom', **FONT_LABEL)

# 3. Backend → ChromaDB (아래로)
arrow3 = FancyArrowPatch(
    (50, 50), (50, 28),
    arrowstyle='<->,head_width=0.6,head_length=0.8',
    color=COLOR_ARROW,
    linewidth=2.5,
    connectionstyle="arc3,rad=0",
    zorder=1
)
ax.add_patch(arrow3)
ax.text(46, 39, 'Embedding', ha='right', va='center', **FONT_LABEL)
ax.text(46, 35, 'Retrieve', ha='right', va='center', **FONT_LABEL)

# 4. Backend → GPT-4
arrow4 = FancyArrowPatch(
    (63, 77.5), (71, 77.5),
    arrowstyle='<->,head_width=0.6,head_length=0.8',
    color=COLOR_ARROW,
    linewidth=2.5,
    zorder=1
)
ax.add_patch(arrow4)
ax.text(67, 79.5, 'Context', ha='center', va='bottom', **FONT_LABEL)
ax.text(67, 75.5, 'Answer', ha='center', va='top', **FONT_LABEL)

# 5. Backend → PostgreSQL (아래로)
arrow5 = FancyArrowPatch(
    (60, 50), (73, 28),
    arrowstyle='<->,head_width=0.6,head_length=0.8',
    color=COLOR_ARROW,
    linewidth=2.5,
    connectionstyle="arc3,rad=0.2",
    zorder=1
)
ax.add_patch(arrow5)
ax.text(64, 38, 'Feedback', ha='center', va='center', **FONT_LABEL)

# 6. Backend → Frontend (응답)
arrow6 = FancyArrowPatch(
    (47, 73), (39, 73),
    arrowstyle='->,head_width=0.6,head_length=0.8',
    color='#4CAF50',
    linewidth=2.5,
    linestyle='--',
    zorder=1
)
ax.add_patch(arrow6)
ax.text(43, 71, 'Response', ha='center', va='top', **FONT_LABEL)

# ============================================
# 제목
# ============================================
ax.text(50, 95, 'LawLaw 시스템 아키텍처', ha='center', va='center', **FONT_TITLE)

# ============================================
# 범례 (아래)
# ============================================
legend_y = 3
ax.text(10, legend_y, '데이터 흐름:', ha='left', va='center', **{'size': 10, 'weight': 'bold', 'color': '#424242'})
ax.text(20, legend_y, '1) User Query → Frontend', ha='left', va='center', **{'size': 9, 'color': '#616161'})
ax.text(38, legend_y, '2) REST API → Backend', ha='left', va='center', **{'size': 9, 'color': '#616161'})
ax.text(54, legend_y, '3) Hybrid Search (ChromaDB)', ha='left', va='center', **{'size': 9, 'color': '#616161'})
ax.text(74, legend_y, '4) GPT-4 → Response', ha='left', va='center', **{'size': 9, 'color': '#616161'})

# ============================================
# 저장
# ============================================
plt.tight_layout()
output_path = '/Users/jaehyungpark/Documents/libraries/lawlaw/docs/architecture/system_architecture_diagram.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ 다이어그램 생성 완료: {output_path}")
plt.close()

print("\n생성된 이미지 정보:")
print(f"- 경로: {output_path}")
print(f"- 해상도: 300 DPI (고품질)")
print(f"- 크기: 약 6000x2100px")
print(f"- 형식: PNG")

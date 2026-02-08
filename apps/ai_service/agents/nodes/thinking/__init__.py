"""
Thinking Agent Nodes - ReAct 패턴 구현

Phase 6: Thinking Agent - 자율 추론 노드

노드 구성:
- think_node: 상황 분석 및 다음 행동 결정 (Phase 6-1)
- act_node: 도구/워크플로우 실행 (Phase 6-1)
- observe_node: 실행 결과 관찰 (Phase 6-2)
- reflect_node: 결과 반성 및 평가 (Phase 6-2)

ReAct 루프:
    Think → Act → Observe → Reflect → (반복 또는 종료)
"""

from apps.ai_service.agents.nodes.thinking.think_node import (
    think_node,
    think_node_sync,
)
from apps.ai_service.agents.nodes.thinking.act_node import (
    act_node,
    act_node_sync,
)
from apps.ai_service.agents.nodes.thinking.observe_node import (
    observe_node,
    observe_node_sync,
)
from apps.ai_service.agents.nodes.thinking.reflect_node import (
    reflect_node,
    reflect_node_sync,
)

__all__ = [
    # Phase 6-1
    "think_node",
    "think_node_sync",
    "act_node",
    "act_node_sync",
    # Phase 6-2
    "observe_node",
    "observe_node_sync",
    "reflect_node",
    "reflect_node_sync",
]

"""
Phase 2 검증 테스트 스크립트
- 모듈 import 테스트
- IntentClassifier 단위 테스트
- WorkflowRouter 단위 테스트
- Master Agent Graph 생성 테스트
"""

import sys
import asyncio

print("=" * 60)
print("Phase 2 구현 검증 시작")
print("=" * 60)

# =====================================================
# 1. 모듈 Import 테스트
# =====================================================
print("\n[1/4] 모듈 Import 테스트")
print("-" * 40)

errors = []
Intent = None
IntentCategory = None
IntentClassifier = None
WorkflowRouter = None
create_master_agent_graph = None

# 1.1 master_agent_state (states/master_agent_state.py)
try:
    from apps.ai_service.agents.states.master_agent_state import (
        MasterAgentState,
        Intent,
        IntentCategory,  # IntentType이 아니라 IntentCategory
        ExecutionPlan,
        WorkflowStep,  # ExecutionStep이 아니라 WorkflowStep
        create_initial_master_agent_state,
    )
    print("✅ master_agent_state 모듈 import 성공")
except Exception as e:
    errors.append(f"master_agent_state: {e}")
    print(f"❌ master_agent_state import 실패: {e}")

# 1.2 intent_classifier (agents/intent_classifier.py)
try:
    from apps.ai_service.agents.intent_classifier import IntentClassifier
    print("✅ intent_classifier 모듈 import 성공")
except Exception as e:
    errors.append(f"intent_classifier: {e}")
    print(f"❌ intent_classifier import 실패: {e}")

# 1.3 workflow_router (agents/workflow_router.py)
try:
    from apps.ai_service.agents.workflow_router import WorkflowRouter
    print("✅ workflow_router 모듈 import 성공")
except Exception as e:
    errors.append(f"workflow_router: {e}")
    print(f"❌ workflow_router import 실패: {e}")

# 1.4 노드 모듈들 (agents/nodes/*.py)
try:
    from apps.ai_service.agents.nodes.classify_intent_node import classify_intent_node
    print("✅ classify_intent_node 모듈 import 성공")
except Exception as e:
    errors.append(f"classify_intent_node: {e}")
    print(f"❌ classify_intent_node import 실패: {e}")

try:
    from apps.ai_service.agents.nodes.plan_execution_node import plan_execution_node
    print("✅ plan_execution_node 모듈 import 성공")
except Exception as e:
    errors.append(f"plan_execution_node: {e}")
    print(f"❌ plan_execution_node import 실패: {e}")

try:
    from apps.ai_service.agents.nodes.execute_workflows_node import execute_workflows_node
    print("✅ execute_workflows_node 모듈 import 성공")
except Exception as e:
    errors.append(f"execute_workflows_node: {e}")
    print(f"❌ execute_workflows_node import 실패: {e}")

try:
    from apps.ai_service.agents.nodes.aggregate_results_node import aggregate_results_node
    print("✅ aggregate_results_node 모듈 import 성공")
except Exception as e:
    errors.append(f"aggregate_results_node: {e}")
    print(f"❌ aggregate_results_node import 실패: {e}")

try:
    from apps.ai_service.agents.nodes.generate_response_node import generate_response_node
    print("✅ generate_response_node 모듈 import 성공")
except Exception as e:
    errors.append(f"generate_response_node: {e}")
    print(f"❌ generate_response_node import 실패: {e}")

# 1.5 master_agent (agents/master_agent.py)
try:
    from apps.ai_service.agents.master_agent import create_master_agent_graph
    print("✅ master_agent 모듈 import 성공")
except Exception as e:
    errors.append(f"master_agent: {e}")
    print(f"❌ master_agent import 실패: {e}")

if errors:
    print(f"\n⚠️ Import 에러 {len(errors)}개 발견")
else:
    print("\n✅ 모든 모듈 import 성공!")

# =====================================================
# 2. IntentClassifier 단위 테스트
# =====================================================
print("\n[2/4] IntentClassifier 단위 테스트")
print("-" * 40)

async def test_intent_classifier():
    """IntentClassifier 비동기 테스트"""
    if IntentClassifier is None:
        print("⚠️ IntentClassifier를 import하지 못해 테스트 건너뜀")
        return

    try:
        classifier = IntentClassifier()

        test_messages = [
            ("판례 2023도12345 내용 알려줘", "SEARCH"),
            ("이 계약서 검토해줘", "DOCUMENT_ANALYSIS"),
            ("사기죄 관련 판례 찾아줘", "SEARCH"),
            ("안녕하세요", "QUERY"),
            ("형법 제250조 설명해줘", "QUERY"),
        ]

        print("샘플 메시지 의도 분류 테스트:")
        for msg, expected in test_messages:
            try:
                intent = await classifier.classify(msg)
                actual_category = intent.category.value if hasattr(intent.category, 'value') else str(intent.category)
                status = "✅" if actual_category == expected else "⚠️"
                print(f"  {status} '{msg[:25]}...' → {actual_category} (예상: {expected})")
                print(f"      신뢰도: {intent.confidence:.2f}, 추천 워크플로우: {intent.suggested_workflows}")
            except Exception as e:
                print(f"  ❌ 분류 실패: {msg[:25]}... - {e}")
    except Exception as e:
        print(f"❌ IntentClassifier 인스턴스 생성 실패: {e}")

# =====================================================
# 3. WorkflowRouter 단위 테스트
# =====================================================
print("\n[3/4] WorkflowRouter 단위 테스트")
print("-" * 40)

async def test_workflow_router():
    """WorkflowRouter 비동기 테스트"""
    if WorkflowRouter is None or Intent is None or IntentCategory is None:
        print("⚠️ WorkflowRouter 또는 Intent를 import하지 못해 테스트 건너뜀")
        return

    try:
        router = WorkflowRouter()

        # 샘플 Intent로 실행 계획 생성 테스트
        test_intents = [
            Intent(
                category=IntentCategory.SEARCH,
                confidence=0.9,
                extracted_params={"search_query": "사기죄 판례"},
                suggested_workflows=["legal_search_workflow"],
            ),
            Intent(
                category=IntentCategory.DOCUMENT_ANALYSIS,
                confidence=0.85,
                extracted_params={"document_type": "계약서"},
                suggested_workflows=["document_analysis_workflow"],
            ),
            Intent(
                category=IntentCategory.QUERY,
                confidence=0.95,
                extracted_params={},
                suggested_workflows=["rag_query_workflow"],
            ),
        ]

        print("샘플 Intent로 실행 계획 생성 테스트:")
        for intent in test_intents:
            try:
                # route 메서드 사용 (async가 아니면 직접 호출)
                plan = router.route(intent)
                print(f"  ✅ Intent({intent.category.value}) → 계획 생성 성공")
                print(f"      계획 ID: {plan.plan_id[:8]}...")
                print(f"      워크플로우 수: {len(plan.workflows)}")
                for step in plan.workflows:
                    print(f"        - {step.workflow_name}: {step.inputs}")
            except Exception as e:
                print(f"  ❌ 계획 생성 실패: {intent.category.value} - {e}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"❌ WorkflowRouter 인스턴스 생성 실패: {e}")
        import traceback
        traceback.print_exc()

# =====================================================
# 4. Master Agent Graph 생성 테스트
# =====================================================
print("\n[4/4] Master Agent Graph 생성 테스트")
print("-" * 40)

def test_master_agent_graph():
    """Master Agent Graph 생성 테스트"""
    if create_master_agent_graph is None:
        print("⚠️ create_master_agent_graph를 import하지 못해 테스트 건너뜀")
        return

    try:
        graph = create_master_agent_graph()
        print("✅ create_master_agent_graph() 호출 성공")
        print(f"   그래프 타입: {type(graph).__name__}")

        # 그래프 노드 확인
        if hasattr(graph, 'nodes'):
            print(f"   노드 수: {len(graph.nodes)}")
            print(f"   노드 목록: {list(graph.nodes.keys())}")

    except Exception as e:
        print(f"❌ Master Agent Graph 생성 실패: {e}")
        import traceback
        traceback.print_exc()

# 비동기 테스트 실행
async def run_all_tests():
    """모든 테스트 실행"""
    await test_intent_classifier()
    print()  # 줄바꿈
    await test_workflow_router()
    print()  # 줄바꿈
    test_master_agent_graph()

# 메인 실행
if __name__ == "__main__":
    asyncio.run(run_all_tests())

    # =====================================================
    # 검증 결과 요약
    # =====================================================
    print("\n" + "=" * 60)
    print("Phase 2 검증 결과 요약")
    print("=" * 60)

    if errors:
        print(f"❌ Import 에러: {len(errors)}개")
        for err in errors:
            print(f"   - {err}")
        print("\n위 에러를 수정해야 합니다.")
    else:
        print("✅ 모든 모듈 import 성공!")
        print("   세부 테스트 결과는 위 출력을 확인하세요.")

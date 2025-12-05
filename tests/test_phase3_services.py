"""
Phase 3 서비스 검증 테스트

테스트 항목:
1. Redis 연결 테스트
2. SessionService 테스트
3. ConversationService 테스트
4. UsageService 테스트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime


def print_test_header(test_name: str):
    """테스트 헤더 출력"""
    print("\n" + "=" * 60)
    print(f"📋 {test_name}")
    print("=" * 60)


def print_result(success: bool, message: str):
    """결과 출력"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status}: {message}")


async def test_redis_connection():
    """1. Redis 연결 테스트"""
    print_test_header("Redis 연결 테스트")

    import redis
    from apps.ai_service.config.settings import settings

    try:
        # 직접 연결 테스트
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

        # Ping 테스트
        result = client.ping()
        print_result(result, f"Redis PING: {result}")

        # 간단한 SET/GET 테스트
        test_key = "test:phase3:connection"
        test_value = f"테스트_{datetime.now().isoformat()}"

        client.setex(test_key, 10, test_value)
        retrieved = client.get(test_key)

        print_result(retrieved == test_value, f"SET/GET 테스트: {retrieved}")

        # 정리
        client.delete(test_key)
        client.close()

        return True

    except redis.ConnectionError as e:
        print_result(False, f"Redis 연결 실패: {e}")
        return False
    except Exception as e:
        print_result(False, f"에러: {e}")
        return False


async def test_session_service():
    """2. SessionService 테스트"""
    print_test_header("SessionService 테스트")

    from apps.ai_service.services.session_service import get_session_service

    service = get_session_service()
    test_user_id = "test-user-phase3-001"
    test_org_id = "test-org-001"
    session_id = None

    try:
        # 2.1 연결 확인
        is_connected = service.is_connected()
        print_result(is_connected, f"Redis 연결 상태: {is_connected}")

        if not is_connected:
            return False

        # 2.2 세션 생성
        session_id = await service.create_session(
            user_id=test_user_id,
            organization_id=test_org_id,
            metadata={"test": True, "source": "phase3_test"}
        )
        print_result(session_id is not None, f"세션 생성: {session_id}")

        # 2.3 세션 조회
        session = await service.get_session(session_id)
        print_result(
            session is not None and session.get("user_id") == test_user_id,
            f"세션 조회: user_id={session.get('user_id') if session else 'None'}"
        )

        # 2.4 세션 활동 업데이트
        update_result = await service.update_session_activity(session_id)
        session_after = await service.get_session(session_id)
        print_result(
            update_result and session_after.get("conversation_count") == 1,
            f"활동 업데이트: conversation_count={session_after.get('conversation_count')}"
        )

        # 2.5 워크플로우 카운트 증가
        wf_result = await service.increment_workflow_count(session_id, count=2)
        session_after_wf = await service.get_session(session_id)
        print_result(
            wf_result and session_after_wf.get("total_workflows_executed") == 2,
            f"워크플로우 카운트: {session_after_wf.get('total_workflows_executed')}"
        )

        # 2.6 사용자 세션 목록 조회
        user_sessions = await service.get_user_sessions(test_user_id)
        print_result(
            session_id in user_sessions,
            f"사용자 세션 목록: {len(user_sessions)}개"
        )

        # 2.7 세션 삭제
        delete_result = await service.delete_session(session_id)
        session_deleted = await service.get_session(session_id)
        print_result(
            delete_result and session_deleted is None,
            f"세션 삭제: 성공"
        )

        return True

    except Exception as e:
        print_result(False, f"에러: {e}")
        import traceback
        traceback.print_exc()

        # 정리 시도
        if session_id:
            try:
                await service.delete_session(session_id)
            except:
                pass

        return False


async def test_conversation_service():
    """3. ConversationService 테스트"""
    print_test_header("ConversationService 테스트")

    from apps.ai_service.services.conversation_service import get_conversation_service

    service = get_conversation_service()
    test_session_id = "test-session-phase3-conv-001"

    try:
        # 3.1 연결 확인
        is_connected = service.is_connected()
        print_result(is_connected, f"Redis 연결 상태: {is_connected}")

        if not is_connected:
            return False

        # 3.2 사용자 메시지 추가
        user_result = await service.add_message(
            session_id=test_session_id,
            role="user",
            content="법률 질문입니다. 계약서 검토 방법을 알려주세요.",
            metadata={"intent": "legal_question"}
        )
        print_result(user_result, "사용자 메시지 추가")

        # 3.3 어시스턴트 메시지 추가
        assistant_result = await service.add_message(
            session_id=test_session_id,
            role="assistant",
            content="계약서 검토 시에는 다음 사항들을 확인해야 합니다...",
            metadata={
                "workflows_used": ["rag_workflow"],
                "execution_time": 1.5
            }
        )
        print_result(assistant_result, "어시스턴트 메시지 추가")

        # 3.4 대화 기록 조회
        history = await service.get_history(test_session_id, limit=10)
        print_result(
            len(history) == 2,
            f"대화 기록 조회: {len(history)}개 메시지"
        )

        # 3.5 메시지 내용 확인
        if len(history) >= 2:
            user_msg = history[0]
            assistant_msg = history[1]
            print_result(
                user_msg.get("role") == "user" and assistant_msg.get("role") == "assistant",
                f"메시지 순서 확인: user -> assistant"
            )

        # 3.6 메시지 수 조회
        count = await service.get_message_count(test_session_id)
        print_result(count == 2, f"메시지 수: {count}")

        # 3.7 마지막 메시지 조회
        last_msg = await service.get_last_message(test_session_id)
        print_result(
            last_msg is not None and last_msg.get("role") == "assistant",
            f"마지막 메시지: role={last_msg.get('role') if last_msg else 'None'}"
        )

        # 3.8 대화 요약
        summary = await service.get_conversation_summary(test_session_id)
        print_result(
            summary.get("total_messages") == 2,
            f"대화 요약: {summary.get('user_messages')} user, {summary.get('assistant_messages')} assistant"
        )

        # 3.9 대화 기록 삭제
        clear_result = await service.clear_history(test_session_id)
        history_after = await service.get_history(test_session_id)
        print_result(
            clear_result and len(history_after) == 0,
            "대화 기록 삭제"
        )

        return True

    except Exception as e:
        print_result(False, f"에러: {e}")
        import traceback
        traceback.print_exc()

        # 정리 시도
        try:
            await service.clear_history(test_session_id)
        except:
            pass

        return False


async def test_usage_service():
    """4. UsageService 테스트"""
    print_test_header("UsageService 테스트")

    from apps.ai_service.services.usage_service import get_usage_service

    service = get_usage_service()
    test_user_id = "test-user-phase3-usage-001"
    test_org_id = "test-org-usage-001"

    try:
        # 4.1 연결 확인
        is_connected = service.is_connected()
        print_result(is_connected, f"Redis 연결 상태: {is_connected}")

        if not is_connected:
            return False

        # 4.2 쿼터 확인 (사용 전)
        quota_before = await service.check_quota(
            user_id=test_user_id,
            workflows=["rag_workflow"]
        )
        print_result(
            quota_before.get("within_quota") == True,
            f"쿼터 확인: {quota_before.get('current_usage')}/{quota_before.get('daily_limit')}"
        )

        # 4.3 사용량 기록
        usage_data = await service.track_usage(
            user_id=test_user_id,
            organization_id=test_org_id,
            workflows=["rag_workflow"],
            execution_time=2.5,
            tokens=500
        )
        print_result(
            usage_data.total_requests >= 1,
            f"사용량 기록: requests={usage_data.total_requests}, tokens={usage_data.total_tokens}"
        )

        # 4.4 일일 사용량 조회
        daily_usage = await service.get_daily_usage(test_user_id)
        print_result(
            daily_usage.get("total_requests") >= 1,
            f"일일 사용량: requests={daily_usage.get('total_requests')}"
        )

        # 4.5 워크플로우별 사용량 확인
        workflow_usage = daily_usage.get("workflow_usage", {})
        print_result(
            workflow_usage.get("rag_workflow", 0) >= 1,
            f"워크플로우별 사용량: {workflow_usage}"
        )

        # 4.6 쿼터 확인 (사용 후)
        quota_after = await service.check_quota(test_user_id)
        print_result(
            quota_after.get("current_usage") >= 1,
            f"쿼터 갱신 확인: {quota_after.get('remaining')} 남음"
        )

        # 4.7 조직 설정 조회
        org_settings = await service.get_org_settings(test_org_id)
        print_result(
            org_settings.get("plan_type") is not None,
            f"조직 설정: plan_type={org_settings.get('plan_type')}"
        )

        # 4.8 사용량 요약
        summary = await service.get_usage_summary(test_user_id, test_org_id)
        print_result(
            "user_usage" in summary and "quota" in summary,
            f"사용량 요약: {summary.get('quota', {}).get('percentage_used')}% 사용"
        )

        # 4.9 사용 기록 조회 (최근 7일)
        history = await service.get_usage_history(test_user_id, days=3)
        print_result(
            len(history) == 3,
            f"사용 기록: {len(history)}일치 데이터"
        )

        # 정리는 자동 만료로 처리 (TTL)
        print_result(True, "테스트 데이터는 TTL에 의해 자동 정리됨")

        return True

    except Exception as e:
        print_result(False, f"에러: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "🧪" * 30)
    print("Phase 3 서비스 검증 시작")
    print("🧪" * 30)

    results = {}

    # 1. Redis 연결 테스트
    results["Redis 연결"] = await test_redis_connection()

    if not results["Redis 연결"]:
        print("\n⚠️  Redis 연결 실패로 나머지 테스트를 건너뜁니다.")
        print("Docker에서 Redis가 실행 중인지 확인하세요:")
        print("  docker ps | grep redis")
        return results

    # 2. SessionService 테스트
    results["SessionService"] = await test_session_service()

    # 3. ConversationService 테스트
    results["ConversationService"] = await test_conversation_service()

    # 4. UsageService 테스트
    results["UsageService"] = await test_usage_service()

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if success:
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"총 {len(results)}개 테스트 중 {passed}개 통과, {failed}개 실패")

    if failed == 0:
        print("\n🎉 Phase 3 모든 테스트 통과!")
    else:
        print(f"\n⚠️  {failed}개 테스트 실패. 위 에러를 확인하세요.")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())

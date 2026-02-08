"""
Intent Classifier - 사용자 의도 분류기

Phase 5: Agent Hub - 의도 분류 컴포넌트

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.1

역할:
- 사용자의 자연어 요청을 분석하여 어떤 기능을 사용해야 하는지 결정
- LLM 기반 의도 분류 수행
- 파라미터 추출 및 워크플로우 추천

의도 카테고리:
1. QUERY: 일반 법률 질의응답
2. DOCUMENT_ANALYSIS: 문서 분석 요청
3. CASE_ANALYSIS: 사건 분석 요청
4. RISK_ASSESSMENT: 리스크 평가 요청
5. COMPARISON: 비교 분석
6. SEARCH: 판례/법령 검색
7. GENERATION: 문서/보고서 생성
8. ANALYTICS: 통계/분석
9. MULTI_TASK: 복합 작업
"""

from typing import List, Dict, Any, Optional
import json
import logging

from apps.ai_service.agents.states.master_agent_state import (
    Intent,
    IntentCategory,
)
from libs.rag_core.llm.llm_client import LLMClient, create_llm_client
from apps.ai_service.config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# 의도 카테고리별 설명 및 키워드
# =============================================================================

INTENT_CATEGORIES = {
    IntentCategory.GENERAL_CHAT: {
        "description": "일반 대화 - 법률과 무관한 인사, 잡담, 일상 대화",
        "examples": [
            "안녕하세요",
            "오늘 날씨 어때?",
            "뭐해?",
            "고마워",
            "잘 있어",
            "너 이름이 뭐야?",
            "점심 뭐 먹었어?",
        ],
        "keywords": ["안녕", "고마워", "감사", "뭐해", "날씨", "이름", "점심", "저녁", "아침"],
        "workflows": [],  # 워크플로우 없음 - LLM 직접 응답
    },
    IntentCategory.QUERY: {
        "description": "일반 법률 질의응답 - 법률 개념, 조문, 절차 등에 대한 질문",
        "examples": [
            "절도죄의 법정형은?",
            "이혼 절차가 어떻게 되나요?",
            "계약 해지 통보 방법은?",
            "민법 제750조가 무엇인가요?",
        ],
        "keywords": ["무엇", "어떻게", "뭐야", "알려줘", "설명해", "정의"],
        "workflows": ["rag_workflow"],
    },
    IntentCategory.DOCUMENT_ANALYSIS: {
        "description": "문서 분석 요청 - 계약서, 소장, 판결문 등의 분석",
        "examples": [
            "이 계약서를 분석해줘",
            "첨부된 문서의 주요 조항을 정리해줘",
            "이 소장의 청구 원인을 분석해줘",
        ],
        "keywords": ["분석해", "검토해", "정리해", "요약해", "문서", "계약서", "소장"],
        "workflows": ["document_workflow"],
    },
    IntentCategory.CASE_ANALYSIS: {
        "description": "사건 분석 요청 - 판례나 법적 사건의 분석",
        "examples": [
            "이 판례의 쟁점은 뭐야?",
            "이 사건의 당사자 관계를 분석해줘",
            "이 판결문에서 핵심 판시사항이 뭐야?",
        ],
        "keywords": ["판례", "사건", "쟁점", "당사자", "판결", "판시"],
        "workflows": ["case_workflow"],
    },
    IntentCategory.RISK_ASSESSMENT: {
        "description": "리스크 평가 요청 - 계약, 거래, 사업의 법적 리스크 분석",
        "examples": [
            "이 계약의 리스크를 평가해줘",
            "이 거래의 법적 위험은?",
            "이 조항의 문제점을 찾아줘",
        ],
        "keywords": ["리스크", "위험", "문제점", "평가해", "취약점", "주의사항"],
        "workflows": ["risk_workflow"],
    },
    IntentCategory.COMPARISON: {
        "description": "비교 분석 - LLM 모델 비교, 문서 비교 등",
        "examples": [
            "GPT-4와 Claude로 비교해줘",
            "두 계약서의 차이점은?",
            "여러 모델로 분석 결과를 비교해줘",
        ],
        "keywords": ["비교", "차이점", "GPT", "Claude", "모델"],
        "workflows": ["llm_comparison_workflow"],
    },
    IntentCategory.SEARCH: {
        "description": "판례/법령 검색 - 관련 판례나 법령 찾기",
        "examples": [
            "절도죄 판례 5개 찾아줘",
            "민법 제750조 관련 판례 검색",
            "최근 명예훼손 판결 보여줘",
        ],
        "keywords": ["찾아", "검색", "조회", "보여줘", "판례", "법령"],
        "workflows": [],
        "tools": ["fetch_court_api", "fetch_statute_api", "search_related_cases"],
    },
    IntentCategory.GENERATION: {
        "description": "문서/보고서 생성 - 법률 문서나 보고서 작성",
        "examples": [
            "분석 보고서를 만들어줘",
            "이 내용으로 소장을 작성해줘",
            "법률 의견서를 생성해줘",
        ],
        "keywords": ["만들어", "작성해", "생성해", "보고서", "문서작성"],
        "workflows": [],
        "tools": ["generate_report"],
    },
    IntentCategory.ANALYTICS: {
        "description": "통계/분석 - 판례 통계, 트렌드 분석 등",
        "examples": [
            "최근 1년 판례 통계 보여줘",
            "절도죄 양형 트렌드 분석해줘",
            "법원별 판결 현황 통계",
        ],
        "keywords": ["통계", "트렌드", "현황", "분석", "추이"],
        "workflows": ["analytics_workflow"],
    },
    IntentCategory.MULTI_TASK: {
        "description": "복합 작업 - 여러 기능을 조합한 복잡한 요청",
        "examples": [
            "이 계약서를 분석하고 리스크를 평가한 뒤 보고서를 만들어줘",
            "판례를 검색해서 비교 분석해줘",
            "문서를 분석하고 GPT-4와 Claude로 비교해줘",
        ],
        "keywords": ["그리고", "한 뒤", "다음에", "후에"],
        "workflows": [],  # 동적으로 결정
    },
}

# 카테고리별 추천 워크플로우 매핑
CATEGORY_WORKFLOW_MAP = {
    IntentCategory.GENERAL_CHAT: [],  # 워크플로우 없음 - LLM 직접 응답
    IntentCategory.QUERY: ["rag_workflow"],
    IntentCategory.DOCUMENT_ANALYSIS: ["document_workflow"],
    IntentCategory.CASE_ANALYSIS: ["case_workflow"],
    IntentCategory.RISK_ASSESSMENT: ["risk_workflow"],
    IntentCategory.COMPARISON: ["llm_comparison_workflow"],
    IntentCategory.SEARCH: [],
    IntentCategory.GENERATION: [],
    IntentCategory.ANALYTICS: ["analytics_workflow"],
    IntentCategory.MULTI_TASK: [],
}


# =============================================================================
# 휴리스틱 기반 일반 대화 감지 (LLM 호출 전 사전 필터링)
# =============================================================================

# 일반 대화로 분류되는 패턴들
GENERAL_CHAT_PATTERNS = {
    # 인사
    "안녕", "하이", "헬로", "hi", "hello", "반가워", "안녕하세요",
    # 감사
    "고마워", "감사", "감사합니다", "고맙습니다", "thanks", "thank you",
    # 작별
    "잘 있어", "잘가", "bye", "바이", "다음에",
    # 상태 질문
    "뭐해", "뭐하는", "어때", "어떠",
    # 자기소개/이름
    "이름이 뭐", "너는 누구", "넌 뭐야", "뭐야", "누구야",
    # 반응
    "ㅎㅎ", "ㅋㅋ", "ㅠㅠ", "ㅜㅜ", "오케이", "오키", "알겠", "네", "응", "어",
    # 날씨/일상
    "날씨", "점심", "저녁", "아침", "밥",
}

# 법률 관련 키워드 - 이 중 하나라도 있으면 법률 관련으로 간주
LEGAL_KEYWORDS = {
    "법", "법률", "법적", "법원", "재판", "소송", "판결", "판례", "조문", "조항",
    "계약", "계약서", "합의", "합의서", "해지", "해제", "위반", "손해배상",
    "민법", "형법", "상법", "행정법", "헌법", "노동법", "세법",
    "피고", "원고", "피해자", "가해자", "변호사", "검사", "판사",
    "기소", "공소", "상고", "항소", "상소",
    "절도", "사기", "폭행", "살인", "강도", "횡령", "배임",
    "이혼", "상속", "유언", "친권", "양육권",
    "임대", "임차", "전세", "월세", "보증금",
    "저작권", "특허", "상표", "지적재산",
    "근로", "해고", "퇴직", "임금", "노동",
    "세금", "증여", "상속세", "소득세",
    "조례", "규정", "시행령", "시행규칙",
    "채권", "채무", "담보", "저당", "질권",
    "죄", "형량", "양형", "선고", "집행유예", "벌금", "징역",
    "민사", "형사", "가사", "행정", "특허",
}


def is_general_chat(message: str) -> bool:
    """
    메시지가 일반 대화인지 휴리스틱으로 판단

    Args:
        message: 사용자 메시지

    Returns:
        일반 대화 여부
    """
    # 공백 제거 및 소문자 변환
    normalized = message.lower().strip()

    # 너무 짧은 메시지 (5자 이하)이면서 법률 키워드가 없으면 일반 대화
    if len(normalized) <= 5:
        for keyword in LEGAL_KEYWORDS:
            if keyword in normalized:
                return False
        return True

    # 법률 키워드가 하나라도 있으면 법률 관련
    for keyword in LEGAL_KEYWORDS:
        if keyword in normalized:
            return False

    # 일반 대화 패턴이 있으면 일반 대화
    for pattern in GENERAL_CHAT_PATTERNS:
        if pattern in normalized:
            return True

    # 질문 형태이지만 법률 키워드가 없는 짧은 질문
    # (15자 이하이고 ? 또는 "뭐" "어떻게" 등이 포함)
    if len(normalized) <= 15:
        question_patterns = ["?", "뭐", "어떻게", "왜", "언제", "누가", "어디"]
        for pattern in question_patterns:
            if pattern in normalized:
                # 법률 키워드가 없으면 일반 대화
                for keyword in LEGAL_KEYWORDS:
                    if keyword in normalized:
                        return False
                return True

    return False


# =============================================================================
# 분류 프롬프트 템플릿
# =============================================================================

CLASSIFICATION_PROMPT_TEMPLATE = """당신은 법률 AI 어시스턴트의 의도 분류 전문가입니다.
사용자의 요청을 분석하여 어떤 기능을 사용해야 하는지 결정하세요.

## 🔴 최우선 판단: 법률 관련성 확인

**먼저 요청이 법률/법적 주제와 관련이 있는지 판단하세요.**

법률과 **무관한** 요청의 예:
- 인사: "안녕하세요", "안녕", "하이", "반가워"
- 잡담: "오늘 날씨 어때?", "뭐해?", "심심해"
- 일상: "점심 뭐 먹었어?", "요즘 어때?"
- 감사/인사: "고마워", "수고해", "잘 있어"
- 질문: "너 이름이 뭐야?", "넌 뭘 할 수 있어?"
- 기타: "ㅎㅎ", "ㅋㅋ", "오케이", "알겠어"

**위와 같이 법률과 무관한 일반 대화는 반드시 GENERAL_CHAT으로 분류하세요!**

## 사용 가능한 기능 카테고리

0. **GENERAL_CHAT**: 일반 대화 (법률과 무관) ⭐ 최우선 확인
   - 예: "안녕하세요", "고마워", "오늘 날씨 어때?", "너 이름이 뭐야?"
   - 법률, 법, 계약, 소송, 판례 등의 키워드가 없고 일상적인 대화

1. **QUERY**: 법률 질의응답
   - 예: "절도죄란?", "이혼 절차는?", "법정형은?"
   - 법률 용어, 법조항, 법적 절차에 대한 질문

2. **DOCUMENT_ANALYSIS**: 문서 분석
   - 예: "이 계약서 분석해줘", "문서 요약해줘"
   - 파일 첨부가 있으면 이 카테고리 가능성 높음

3. **CASE_ANALYSIS**: 사건/판례 분석
   - 예: "이 판례의 쟁점은?", "당사자 관계 분석"

4. **RISK_ASSESSMENT**: 리스크 평가
   - 예: "리스크를 평가해줘", "법적 위험 분석"

5. **COMPARISON**: 비교 분석
   - 예: "GPT-4와 Claude로 비교해줘", "두 문서 차이점"

6. **SEARCH**: 판례/법령 검색
   - 예: "절도죄 판례 찾아줘", "법령 검색"

7. **GENERATION**: 문서/보고서 생성
   - 예: "보고서 만들어줘", "소장 작성해줘"

8. **ANALYTICS**: 통계/분석
   - 예: "판례 통계 보여줘", "트렌드 분석"

9. **MULTI_TASK**: 여러 작업 조합
   - 예: "분석하고 비교하고 보고서 만들어줘"

## 입력 정보

### 사용자 메시지
{user_message}

### 첨부 파일
{attachments}

### 대화 기록 (최근 {history_count}개)
{conversation_history}

## 응답 형식

다음 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:

```json
{{
    "category": "카테고리명 (위 10가지 중 하나)",
    "sub_category": "세부 카테고리 (선택, 예: contract, litigation)",
    "confidence": 0.0-1.0 사이의 신뢰도,
    "extracted_params": {{
        "doc_type": "문서 타입 (있는 경우)",
        "legal_domain": "법률 분야 (있는 경우)",
        "specific_request": "구체적 요청 사항"
    }},
    "requires_attachment": true/false,
    "suggested_workflows": ["추천 워크플로우 목록"],
    "clarification_needed": true/false,
    "clarification_questions": ["추가 확인이 필요한 질문들"]
}}
```

## 분류 가이드라인

1. **🔴 최우선**: 법률과 무관한 일상 대화, 인사, 잡담은 **GENERAL_CHAT**으로 분류
2. **파일 첨부**가 있으면 DOCUMENT_ANALYSIS나 CASE_ANALYSIS 가능성 높음
3. **여러 작업**을 요청하면 MULTI_TASK로 분류
4. **모델 비교** 요청이 있으면 COMPARISON으로 분류
5. **판례/법령 검색** 명시적 요청이 있으면 SEARCH로 분류
6. **보고서 생성** 요청이 있으면 GENERATION으로 분류
7. 확신이 낮으면 clarification_needed를 true로 설정
8. GENERAL_CHAT일 경우 suggested_workflows는 빈 배열 []로 설정"""


# =============================================================================
# IntentClassifier 클래스
# =============================================================================

class IntentClassifier:
    """
    사용자 의도 분류기

    LLM 기반으로 사용자 메시지를 분석하여 의도를 파악합니다.

    Attributes:
        llm: LLM 클라이언트
        temperature: LLM 온도 설정 (낮을수록 결정적)
        max_tokens: 최대 토큰 수
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ):
        """
        IntentClassifier 초기화

        Args:
            llm_client: LLM 클라이언트 (None이면 설정에서 생성)
            temperature: LLM 온도 (기본값: 0.0, 결정적 출력)
            max_tokens: 최대 토큰 수
        """
        if llm_client:
            self.llm = llm_client
        else:
            # 설정에서 LLM 클라이언트 생성
            self.llm = create_llm_client(
                provider=settings.LLM_PROVIDER,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL,
                base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        self.temperature = temperature
        self.max_tokens = max_tokens

        logger.info(f"IntentClassifier initialized with {settings.LLM_PROVIDER}/{settings.LLM_MODEL}")

    async def classify(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Intent:
        """
        의도 분류 실행

        Args:
            user_message: 사용자 메시지
            conversation_history: 대화 기록 (최근 N개)
            attachments: 첨부 파일 정보

        Returns:
            Intent 객체 (분류 결과)
        """
        try:
            # 0. 휴리스틱 기반 사전 필터링 - 일반 대화 빠르게 감지
            if not attachments and is_general_chat(user_message):
                logger.info(f"[Heuristic] Detected GENERAL_CHAT: {user_message[:50]}...")
                return Intent(
                    category=IntentCategory.GENERAL_CHAT,
                    confidence=0.95,
                    suggested_workflows=[],
                )

            # 1. 분류 프롬프트 생성
            prompt = self._build_classification_prompt(
                user_message=user_message,
                conversation_history=conversation_history,
                attachments=attachments,
            )

            # 2. LLM 호출
            logger.debug(f"Classifying intent for: {user_message[:100]}...")
            response = self.llm.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # 3. 결과 파싱
            intent = self._parse_classification_result(response)

            # 4. 후처리 (파일 첨부 확인 등)
            intent = self._post_process_intent(intent, attachments)

            # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
            category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category
            logger.info(
                f"Intent classified: category={category_value}, "
                f"confidence={intent.confidence:.2f}"
            )

            return intent

        except Exception as e:
            logger.error(f"Intent classification failed: {e}", exc_info=True)
            # 분류 실패 시 기본 의도 반환
            return Intent(
                category=IntentCategory.QUERY,
                confidence=0.3,
                clarification_needed=True,
                clarification_questions=["요청 내용을 조금 더 구체적으로 말씀해 주시겠어요?"],
            )

    def classify_sync(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Intent:
        """
        의도 분류 실행 (동기 버전)

        Args:
            user_message: 사용자 메시지
            conversation_history: 대화 기록 (최근 N개)
            attachments: 첨부 파일 정보

        Returns:
            Intent 객체 (분류 결과)
        """
        try:
            # 0. 휴리스틱 기반 사전 필터링 - 일반 대화 빠르게 감지
            if not attachments and is_general_chat(user_message):
                logger.info(f"[Heuristic] Detected GENERAL_CHAT: {user_message[:50]}...")
                return Intent(
                    category=IntentCategory.GENERAL_CHAT,
                    confidence=0.95,
                    suggested_workflows=[],
                )

            # 1. 분류 프롬프트 생성
            prompt = self._build_classification_prompt(
                user_message=user_message,
                conversation_history=conversation_history,
                attachments=attachments,
            )

            # 2. LLM 호출 (동기)
            logger.debug(f"Classifying intent for: {user_message[:100]}...")
            response = self.llm.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # 3. 결과 파싱
            intent = self._parse_classification_result(response)

            # 4. 후처리
            intent = self._post_process_intent(intent, attachments)

            # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
            category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category
            logger.info(
                f"Intent classified: category={category_value}, "
                f"confidence={intent.confidence:.2f}"
            )

            return intent

        except Exception as e:
            logger.error(f"Intent classification failed: {e}", exc_info=True)
            return Intent(
                category=IntentCategory.QUERY,
                confidence=0.3,
                clarification_needed=True,
                clarification_questions=["요청 내용을 조금 더 구체적으로 말씀해 주시겠어요?"],
            )

    def _build_classification_prompt(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        attachments: Optional[List[Dict[str, Any]]],
    ) -> str:
        """
        분류 프롬프트 생성

        Args:
            user_message: 사용자 메시지
            conversation_history: 대화 기록
            attachments: 첨부 파일 정보

        Returns:
            완성된 프롬프트 문자열
        """
        # 첨부 파일 정보 포맷팅
        if attachments:
            attachments_str = json.dumps(
                [
                    {
                        "filename": a.get("filename", "unknown"),
                        "type": a.get("type", "unknown"),
                        "mime_type": a.get("mime_type", "unknown"),
                    }
                    for a in attachments
                ],
                ensure_ascii=False,
                indent=2,
            )
        else:
            attachments_str = "없음"

        # 대화 기록 포맷팅 (최근 5개만)
        if conversation_history:
            recent_history = conversation_history[-5:]
            history_str = "\n".join(
                [
                    f"- {msg.get('role', 'unknown')}: {msg.get('content', '')[:200]}"
                    for msg in recent_history
                ]
            )
            history_count = len(recent_history)
        else:
            history_str = "없음"
            history_count = 0

        # 프롬프트 생성
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            user_message=user_message,
            attachments=attachments_str,
            conversation_history=history_str,
            history_count=history_count,
        )

        return prompt

    def _parse_classification_result(self, llm_response: str) -> Intent:
        """
        LLM 응답 파싱

        Args:
            llm_response: LLM 응답 텍스트

        Returns:
            Intent 객체
        """
        try:
            # JSON 부분 추출
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                raise ValueError("JSON not found in LLM response")

            json_str = llm_response[json_start:json_end]
            result = json.loads(json_str)

            # 카테고리 파싱
            category_str = result.get("category", "UNKNOWN").upper()
            try:
                category = IntentCategory(category_str)
            except ValueError:
                logger.warning(f"Unknown category: {category_str}, defaulting to QUERY")
                category = IntentCategory.QUERY

            # Intent 객체 생성
            intent = Intent(
                category=category,
                sub_category=result.get("sub_category"),
                confidence=float(result.get("confidence", 0.5)),
                extracted_params=result.get("extracted_params", {}),
                requires_attachment=result.get("requires_attachment", False),
                suggested_workflows=result.get(
                    "suggested_workflows",
                    CATEGORY_WORKFLOW_MAP.get(category, []),
                ),
                clarification_needed=result.get("clarification_needed", False),
                clarification_questions=result.get("clarification_questions", []),
            )

            return intent

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.debug(f"LLM response: {llm_response}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse classification result: {e}")
            raise

    def _post_process_intent(
        self,
        intent: Intent,
        attachments: Optional[List[Dict[str, Any]]],
    ) -> Intent:
        """
        의도 후처리

        - 파일 첨부 확인
        - 워크플로우 추천 보완
        - 신뢰도 조정

        Args:
            intent: 분류된 의도
            attachments: 첨부 파일 정보

        Returns:
            후처리된 Intent 객체
        """
        # 파일 첨부가 있는데 QUERY로 분류된 경우 조정
        if attachments and intent.category == IntentCategory.QUERY:
            # 신뢰도가 낮으면 DOCUMENT_ANALYSIS로 변경 고려
            if intent.confidence < 0.7:
                logger.info(
                    "Adjusting category from QUERY to DOCUMENT_ANALYSIS "
                    "due to file attachment"
                )
                intent.category = IntentCategory.DOCUMENT_ANALYSIS
                intent.suggested_workflows = ["document_workflow"]
                intent.confidence = max(intent.confidence, 0.6)

        # 워크플로우 추천이 비어있으면 기본값 설정
        if not intent.suggested_workflows:
            default_workflows = CATEGORY_WORKFLOW_MAP.get(intent.category, [])
            if default_workflows:
                intent.suggested_workflows = default_workflows

        # MULTI_TASK인 경우 하위 작업 워크플로우 추가
        if intent.category == IntentCategory.MULTI_TASK:
            # extracted_params에서 하위 작업 추출
            sub_tasks = intent.extracted_params.get("sub_tasks", [])
            for sub_task in sub_tasks:
                try:
                    sub_category = IntentCategory(sub_task.upper())
                    sub_workflows = CATEGORY_WORKFLOW_MAP.get(sub_category, [])
                    for wf in sub_workflows:
                        if wf not in intent.suggested_workflows:
                            intent.suggested_workflows.append(wf)
                except ValueError:
                    pass

        return intent


# =============================================================================
# 편의 함수
# =============================================================================

def get_intent_classifier(
    llm_client: Optional[LLMClient] = None,
) -> IntentClassifier:
    """
    IntentClassifier 인스턴스 생성 (싱글톤 패턴 대신 팩토리 사용)

    Args:
        llm_client: LLM 클라이언트 (선택)

    Returns:
        IntentClassifier 인스턴스
    """
    return IntentClassifier(llm_client=llm_client)

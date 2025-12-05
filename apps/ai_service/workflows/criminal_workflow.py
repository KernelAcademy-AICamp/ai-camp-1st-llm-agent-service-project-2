"""
Criminal Case Analysis Workflow

형사 사건 분석 LangGraph 워크플로우

워크플로우 흐름:
1. detect_crime_node: 범죄 유형 감지
2. plan_analysis_node: 범죄 카테고리별 분석 계획 수립
3. [조건부 분기] route_by_category:
   - property: analyze_property_crime → common_analysis
   - violent: analyze_violent_crime → common_analysis
   - traffic: analyze_traffic_crime → common_analysis
   - general: common_analysis
4. common_analysis:
   - analyze_elements_node: 구성요건 분석
   - extract_factors_node: 양형인자 추출
   - estimate_sentence_node: 양형 예측
5. suggest_defense_node: 변호 전략 제안
6. search_precedents_node: 판례 검색
7. aggregate_node: 결과 집계

사용:
    from apps.ai_service.workflows.criminal_workflow import CriminalCaseWorkflow

    workflow = CriminalCaseWorkflow()
    result = await workflow.arun(
        texts=["문서 내용..."],
        filenames=["기소장.pdf"],
        user_id="user-123"
    )
"""

from typing import Dict, Any, Optional, List
import logging
import json
import re

from langgraph.graph import StateGraph, START, END

from apps.ai_service.workflows.base import BaseWorkflow
from apps.ai_service.workflows.states.criminal_state import (
    CriminalCaseState,
    CrimeElementsResult,
    CrimeElementResult,
    SentencingFactorsResult,
    ExpectedSentenceResult,
    CriminalPrecedentResult,
    get_crime_category,
    detect_criminal_stage,
    CRIME_CATEGORY_MAP,
)

logger = logging.getLogger(__name__)


# 한국 형법 주요 범죄 유형 목록
CRIME_TYPES = [
    "절도", "강도", "사기", "횡령", "배임",
    "폭행", "상해", "살인", "강간", "성추행",
    "마약", "음주운전", "교통사고",
    "명예훼손", "모욕", "협박",
    "뇌물", "직무유기", "위증",
]


# ============================================================================
# Node Functions
# ============================================================================

async def detect_crime_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    범죄 유형 감지 노드

    사용자 지정 범죄 유형이 있으면 사용, 없으면 LLM으로 감지
    """
    logger.info("[detect_crime_node] Detecting crime type")

    try:
        # 사용자 지정 범죄 유형 확인
        if state.get("input_crime_type"):
            crime_type = state["input_crime_type"]
            logger.info(f"[detect_crime_node] Using user-specified crime type: {crime_type}")
        else:
            # LLM으로 감지
            from libs.rag_core.llm.llm_client import get_llm_client
            llm_client = get_llm_client()

            texts = state.get("texts", [])
            combined_text = "\n\n".join(texts)[:5000]

            # 휴리스틱 먼저 시도
            crime_type = None
            text_lower = combined_text.lower()
            for crime in CRIME_TYPES:
                if crime in text_lower:
                    crime_type = crime
                    break

            # 휴리스틱 실패 시 LLM 사용
            if not crime_type:
                prompt = f"""다음 법률 문서에서 범죄 유형을 식별하세요.

문서 (첫 3000자):
{combined_text[:3000]}

가능한 범죄 유형:
{', '.join(CRIME_TYPES)}

위 목록에서 가장 적합한 범죄 유형 하나만 응답하세요.
다른 설명 없이 범죄 유형만 출력하세요.
"""
                response = llm_client.generate(prompt=prompt, temperature=0.1, max_tokens=50)
                response_clean = response.strip()

                for crime in CRIME_TYPES:
                    if crime in response_clean:
                        crime_type = crime
                        break

                if not crime_type:
                    crime_type = response_clean[:20]

            logger.info(f"[detect_crime_node] Detected crime type: {crime_type}")

        # 카테고리 결정
        crime_category = get_crime_category(crime_type)
        logger.info(f"[detect_crime_node] Crime category: {crime_category}")

        # 형사 절차 단계 감지
        texts = state.get("texts", [])
        filenames = state.get("filenames", [])
        combined_text = "\n\n".join(texts)
        criminal_stage = detect_criminal_stage(combined_text, filenames)
        logger.info(f"[detect_crime_node] Criminal stage: {criminal_stage}")

        return {
            "crime_type": crime_type,
            "crime_category": crime_category,
            "criminal_stage": criminal_stage,
            "completed_tasks": state.get("completed_tasks", []) + ["detect_crime"]
        }

    except Exception as e:
        logger.error(f"[detect_crime_node] Error: {e}")
        return {
            "crime_type": "미상",
            "crime_category": "general",
            "criminal_stage": "COMPLAINT",
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["detect_crime_failed"]
        }


async def plan_analysis_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    분석 계획 수립 노드

    범죄 카테고리에 따라 분석 계획 수립
    skip_precedents가 True면 판례 검색을 스킵 (비동기 검색을 위해)
    """
    logger.info("[plan_analysis_node] Planning analysis")

    crime_category = state.get("crime_category", "general")
    skip_precedents = state.get("skip_precedents", False)

    # 기본 분석 계획 (판례 검색 제외)
    base_plan = ["analyze_elements", "extract_factors", "estimate_sentence", "suggest_defense"]

    # skip_precedents가 False면 판례 검색 포함
    if not skip_precedents:
        base_plan.append("search_precedents")

    # 카테고리별 추가 분석
    if crime_category == "property":
        analysis_plan = ["analyze_property"] + base_plan
    elif crime_category == "violent":
        analysis_plan = ["analyze_violent"] + base_plan
    elif crime_category == "traffic":
        analysis_plan = ["analyze_traffic"] + base_plan
    else:
        analysis_plan = base_plan

    logger.info(f"[plan_analysis_node] Analysis plan: {analysis_plan}, skip_precedents={skip_precedents}")

    # precedents_status 설정
    precedents_status = "pending" if skip_precedents else None

    return {
        "analysis_plan": analysis_plan,
        "precedents_status": precedents_status,
        "completed_tasks": state.get("completed_tasks", []) + ["plan_analysis"]
    }


def route_by_category(state: CriminalCaseState) -> str:
    """
    범죄 카테고리에 따라 라우팅
    """
    category = state.get("crime_category", "general")
    plan = state.get("analysis_plan", [])

    if plan and plan[0] == "analyze_property":
        return "property"
    elif plan and plan[0] == "analyze_violent":
        return "violent"
    elif plan and plan[0] == "analyze_traffic":
        return "traffic"
    else:
        return "general"


def route_after_defense(state: CriminalCaseState) -> str:
    """
    변호 전략 제안 후 라우팅
    skip_precedents가 True면 판례 검색 스킵하고 바로 aggregate로
    """
    skip_precedents = state.get("skip_precedents", False)
    if skip_precedents:
        return "aggregate"
    else:
        return "search_precedents"


async def analyze_property_crime_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    재산범죄 특화 분석 노드 (절도, 사기, 횡령 등)

    피해액 중심 분석
    """
    logger.info("[analyze_property_crime_node] Analyzing property crime")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        texts = state.get("texts", [])
        combined_text = "\n\n".join(texts)[:5000]
        crime_type = state.get("crime_type", "재산범죄")

        prompt = f"""다음 {crime_type} 사건에서 재산범죄 관련 정보를 분석하세요.

문서:
{combined_text}

분석 항목:
1. 피해액 규모 및 산정 근거
2. 피해 회복 여부 (변제, 합의금 등)
3. 범행 수법 (단순/계획적/조직적)
4. 피해자 수

JSON 형식으로 응답:
{{
    "damage_amount": "피해액 (예: 5000만원)",
    "recovery_status": "피해 회복 상태",
    "method": "범행 수법",
    "victim_count": 피해자 수
}}"""

        response = llm_client.generate(prompt=prompt, temperature=0.1, max_tokens=500)

        # JSON 파싱 (결과는 summary에 추가)
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                property_analysis = json.loads(json_match.group(0))
                summary_addition = f"\n[재산범죄 분석]\n- 피해액: {property_analysis.get('damage_amount', '미상')}\n- 피해회복: {property_analysis.get('recovery_status', '미상')}\n- 범행수법: {property_analysis.get('method', '미상')}"
            else:
                summary_addition = ""
        except:
            summary_addition = ""

        # analysis_plan에서 제거
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_property"]

        return {
            "summary": (state.get("summary") or "") + summary_addition,
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_property"]
        }

    except Exception as e:
        logger.error(f"[analyze_property_crime_node] Error: {e}")
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_property"]
        return {
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_property_failed"]
        }


async def analyze_violent_crime_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    폭력범죄 특화 분석 노드 (폭행, 상해, 살인 등)

    상해 정도 중심 분석
    """
    logger.info("[analyze_violent_crime_node] Analyzing violent crime")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        texts = state.get("texts", [])
        combined_text = "\n\n".join(texts)[:5000]
        crime_type = state.get("crime_type", "폭력범죄")

        prompt = f"""다음 {crime_type} 사건에서 폭력범죄 관련 정보를 분석하세요.

문서:
{combined_text}

분석 항목:
1. 상해 정도 (경미/중등/중상/사망)
2. 치료 기간
3. 흉기 사용 여부
4. 우발적/계획적 여부
5. 정당방위/과잉방위 가능성

JSON 형식으로 응답:
{{
    "injury_level": "상해 정도",
    "treatment_period": "치료 기간",
    "weapon_used": true/false,
    "premeditated": true/false,
    "self_defense_possibility": "정당방위 가능성"
}}"""

        response = llm_client.generate(prompt=prompt, temperature=0.1, max_tokens=500)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                violent_analysis = json.loads(json_match.group(0))
                summary_addition = f"\n[폭력범죄 분석]\n- 상해정도: {violent_analysis.get('injury_level', '미상')}\n- 치료기간: {violent_analysis.get('treatment_period', '미상')}\n- 흉기사용: {'예' if violent_analysis.get('weapon_used') else '아니오'}"
            else:
                summary_addition = ""
        except:
            summary_addition = ""

        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_violent"]

        return {
            "summary": (state.get("summary") or "") + summary_addition,
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_violent"]
        }

    except Exception as e:
        logger.error(f"[analyze_violent_crime_node] Error: {e}")
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_violent"]
        return {
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_violent_failed"]
        }


async def analyze_traffic_crime_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    교통범죄 특화 분석 노드 (음주운전, 교통사고 등)

    혈중농도, 전과 중심 분석
    """
    logger.info("[analyze_traffic_crime_node] Analyzing traffic crime")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        texts = state.get("texts", [])
        combined_text = "\n\n".join(texts)[:5000]
        crime_type = state.get("crime_type", "교통범죄")

        prompt = f"""다음 {crime_type} 사건에서 교통범죄 관련 정보를 분석하세요.

문서:
{combined_text}

분석 항목:
1. 혈중알코올농도 (BAC)
2. 동종전과 횟수 (음주운전 전력)
3. 인적 피해 여부
4. 물적 피해 규모
5. 도주 여부

JSON 형식으로 응답:
{{
    "bac_level": "혈중알코올농도 (예: 0.12%)",
    "prior_dui_count": 동종전과 횟수,
    "personal_injury": "인적 피해",
    "property_damage": "물적 피해",
    "hit_and_run": true/false
}}"""

        response = llm_client.generate(prompt=prompt, temperature=0.1, max_tokens=500)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                traffic_analysis = json.loads(json_match.group(0))
                summary_addition = f"\n[교통범죄 분석]\n- 혈중농도: {traffic_analysis.get('bac_level', '미상')}\n- 동종전과: {traffic_analysis.get('prior_dui_count', 0)}회\n- 도주여부: {'예' if traffic_analysis.get('hit_and_run') else '아니오'}"
            else:
                summary_addition = ""
        except:
            summary_addition = ""

        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_traffic"]

        return {
            "summary": (state.get("summary") or "") + summary_addition,
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_traffic"]
        }

    except Exception as e:
        logger.error(f"[analyze_traffic_crime_node] Error: {e}")
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_traffic"]
        return {
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_traffic_failed"]
        }


async def analyze_elements_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    구성요건 분석 노드

    기존 CaseAnalyzer._analyze_crime_elements() 래핑
    """
    logger.info("[analyze_elements_node] Analyzing crime elements")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        texts = state.get("texts", [])
        combined_text = "\n\n".join(texts)[:5000]
        crime_type = state.get("crime_type", "범죄")

        prompt = f"""다음 {crime_type} 사건에서 구성요건을 분석하세요.

문서:
{combined_text}

분석 항목:
1. 객관적 구성요건 (행위, 객체, 결과)
2. 주관적 구성요건 (고의/과실, 목적)
3. 각 요건의 충족 여부

JSON 형식으로만 응답하세요:
{{
    "objective": [
        {{"element": "요건명", "description": "설명", "fulfilled": true/false}}
    ],
    "subjective": [
        {{"element": "요건명", "description": "설명", "fulfilled": true/false}}
    ]
}}"""

        response = llm_client.generate(prompt=prompt, temperature=0.1, max_tokens=1000)

        # JSON 파싱
        objective: List[CrimeElementResult] = []
        subjective: List[CrimeElementResult] = []

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

                for e in data.get("objective", []):
                    objective.append({
                        "element": e.get("element", ""),
                        "description": e.get("description", ""),
                        "fulfilled": e.get("fulfilled", False),
                    })
                for e in data.get("subjective", []):
                    subjective.append({
                        "element": e.get("element", ""),
                        "description": e.get("description", ""),
                        "fulfilled": e.get("fulfilled", False),
                    })
        except Exception as e:
            logger.warning(f"Failed to parse crime elements: {e}")
            objective = [{"element": "분석 필요", "description": "상세 분석이 필요합니다", "fulfilled": False}]
            subjective = [{"element": "분석 필요", "description": "상세 분석이 필요합니다", "fulfilled": False}]

        crime_elements: CrimeElementsResult = {
            "objective": objective,
            "subjective": subjective,
        }

        logger.info(f"[analyze_elements_node] Found {len(objective)} objective, {len(subjective)} subjective elements")

        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_elements"]

        return {
            "crime_elements": crime_elements,
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_elements"]
        }

    except Exception as e:
        logger.error(f"[analyze_elements_node] Error: {e}")
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "analyze_elements"]
        return {
            "crime_elements": {"objective": [], "subjective": []},
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_elements_failed"]
        }


async def extract_factors_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    양형인자 추출 노드

    기존 CaseAnalyzer._extract_sentencing_factors() 래핑
    """
    logger.info("[extract_factors_node] Extracting sentencing factors")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        texts = state.get("texts", [])
        combined_text = "\n\n".join(texts)[:5000]
        crime_type = state.get("crime_type", "범죄")

        prompt = f"""다음 {crime_type} 사건에서 양형인자를 추출하세요.

문서:
{combined_text}

양형인자 분류:
- 유리한 정상: 초범, 반성, 피해회복, 합의, 자수, 우발적 범행, 고령, 건강문제 등
- 불리한 정상: 동종전과, 계획적 범행, 피해 중대, 범행 후 태도 불량, 피해자 다수 등

JSON 형식으로만 응답하세요:
{{
    "favorable": ["인자1", "인자2"],
    "unfavorable": ["인자1", "인자2"]
}}"""

        response = llm_client.generate(prompt=prompt, temperature=0.1, max_tokens=500)

        favorable: List[str] = []
        unfavorable: List[str] = []

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                favorable = data.get("favorable", [])
                unfavorable = data.get("unfavorable", [])
        except Exception as e:
            logger.warning(f"Failed to parse sentencing factors: {e}")

        sentencing_factors: SentencingFactorsResult = {
            "favorable": favorable,
            "unfavorable": unfavorable,
        }

        logger.info(f"[extract_factors_node] Found {len(favorable)} favorable, {len(unfavorable)} unfavorable factors")

        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "extract_factors"]

        return {
            "sentencing_factors": sentencing_factors,
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["extract_factors"]
        }

    except Exception as e:
        logger.error(f"[extract_factors_node] Error: {e}")
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "extract_factors"]
        return {
            "sentencing_factors": {"favorable": [], "unfavorable": []},
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["extract_factors_failed"]
        }


async def estimate_sentence_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    양형 예측 노드

    기존 CaseAnalyzer._estimate_sentence() 래핑
    """
    logger.info("[estimate_sentence_node] Estimating sentence")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        crime_type = state.get("crime_type", "범죄")
        factors = state.get("sentencing_factors", {"favorable": [], "unfavorable": []})

        prompt = f"""다음 조건에서 예상 양형을 산정하세요.

범죄 유형: {crime_type}
유리한 정상: {', '.join(factors.get('favorable', [])) or '없음'}
불리한 정상: {', '.join(factors.get('unfavorable', [])) or '없음'}

대법원 양형기준 및 유사 판례를 참고하여:
1. 예상 형량 범위
2. 집행유예 가능성 (0.0 ~ 1.0)
3. 산정 근거

JSON 형식으로만 응답하세요:
{{
    "range": "징역 X월 ~ Y년",
    "suspended_probability": 0.0~1.0,
    "reasoning": "산정 근거"
}}"""

        response = llm_client.generate(prompt=prompt, temperature=0.2, max_tokens=500)

        expected_sentence: ExpectedSentenceResult = {
            "range": "개별 사안에 따라 다름",
            "suspended_probability": 0.5,
            "reasoning": "상세 분석 필요",
        }

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

                prob = data.get("suspended_probability", 0.5)
                if isinstance(prob, str):
                    prob = float(prob.replace("%", "")) / 100 if "%" in prob else float(prob)
                prob = max(0.0, min(1.0, prob))

                expected_sentence = {
                    "range": data.get("range", "판단 필요"),
                    "suspended_probability": prob,
                    "reasoning": data.get("reasoning"),
                }
        except Exception as e:
            logger.warning(f"Failed to parse sentence estimation: {e}")

        logger.info(f"[estimate_sentence_node] Estimated: {expected_sentence['range']}")

        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "estimate_sentence"]

        return {
            "expected_sentence": expected_sentence,
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["estimate_sentence"]
        }

    except Exception as e:
        logger.error(f"[estimate_sentence_node] Error: {e}")
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "estimate_sentence"]
        return {
            "expected_sentence": {
                "range": "판단 불가",
                "suspended_probability": 0.5,
                "reasoning": f"분석 실패: {str(e)}",
            },
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["estimate_sentence_failed"]
        }


async def suggest_defense_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    변호 전략 제안 노드

    기존 CaseAnalyzer._suggest_defense_strategies() 래핑
    """
    logger.info("[suggest_defense_node] Suggesting defense strategies")

    try:
        crime_type = state.get("crime_type", "범죄")
        elements = state.get("crime_elements", {"objective": [], "subjective": []})
        factors = state.get("sentencing_factors", {"favorable": [], "unfavorable": []})

        strategies = []

        # 1. 구성요건 미충족 시 무죄/혐의없음 주장
        all_elements = elements.get("objective", []) + elements.get("subjective", [])
        unfulfilled = [e for e in all_elements if not e.get("fulfilled", True)]
        if unfulfilled:
            elements_str = ", ".join([e.get("element", "") for e in unfulfilled])
            strategies.append(f"구성요건 미충족 주장 ({elements_str})")

        # 2. 유리한 양형인자 강조
        favorable = factors.get("favorable", [])
        if favorable:
            strategies.append(f"유리한 정상 강조 ({', '.join(favorable[:3])})")

        # 3. 피해회복 권장
        if "피해회복" not in favorable and "합의" not in favorable:
            strategies.append("피해자 합의 및 피해회복 시도")

        # 4. 일반적인 전략
        strategies.extend([
            "반성 및 재범방지 의지 표명",
            "양형 감경 사유 추가 발굴",
        ])

        # 5. 범죄 유형별 특화 전략
        if crime_type in ["절도", "사기", "횡령"]:
            strategies.append("피해금액 변상 및 공탁")
        elif crime_type in ["폭행", "상해"]:
            strategies.append("우발적 범행 또는 정당방위 주장 검토")
        elif crime_type == "음주운전":
            strategies.append("알코올 치료 프로그램 이수")

        strategies = strategies[:6]  # 최대 6개

        logger.info(f"[suggest_defense_node] Suggested {len(strategies)} strategies")

        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "suggest_defense"]

        return {
            "defense_strategies": strategies,
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["suggest_defense"]
        }

    except Exception as e:
        logger.error(f"[suggest_defense_node] Error: {e}")
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "suggest_defense"]
        return {
            "defense_strategies": ["전문 변호사 상담 권장"],
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["suggest_defense_failed"]
        }


async def search_precedents_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    판례 검색 노드

    글로벌 HybridRetriever 사용 (main.py에서 초기화됨)
    """
    logger.info("[search_precedents_node] Searching precedents")

    try:
        crime_type = state.get("crime_type", "범죄")
        elements = state.get("crime_elements", {"objective": [], "subjective": []})
        summary = state.get("summary", "")

        # 검색 쿼리 생성 - 범죄 유형 + 요약 활용
        objective_elements = elements.get("objective", [])
        element_keywords = " ".join([e.get("element", "") for e in objective_elements[:2]])

        # 요약에서 핵심 키워드 추출
        summary_keywords = summary[:150] if summary else ""
        query = f"{crime_type} 판례 {element_keywords} {summary_keywords}".strip()

        logger.info(f"[search_precedents_node] Query: {query[:100]}...")

        precedents: List[CriminalPrecedentResult] = []

        try:
            # 글로벌 HybridRetriever 사용 (main.py에서 초기화됨)
            from apps.ai_service.workflows.nodes.rag_nodes import _get_global_retriever

            retriever = _get_global_retriever()
            if retriever is None:
                logger.warning("[search_precedents_node] Global retriever not available, using fallback")
                # Fallback: 직접 retriever 생성
                from libs.rag_core.retrieval.hybrid_retriever import HybridRetriever
                from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
                from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
                from libs.rag_core.retrieval.bm25_index import BM25Index
                from apps.ai_service.config.settings import settings

                embedder = RemoteEmbedder()
                vectordb = QdrantVectorDB(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY or None,
                    collection_name=settings.QDRANT_COLLECTION
                )
                bm25_index = BM25Index()
                bm25_index.load(settings.BM25_INDEX_PATH)

                retriever = HybridRetriever(
                    vectordb=vectordb,
                    embedder=embedder,
                    bm25_index=bm25_index
                )

            # HybridRetriever로 검색 (필터 없이) - 동기 메서드 사용
            results = retriever.retrieve(query=query, top_k=5)

            for result in results:
                metadata = result.get("metadata", {})
                text = result.get("text", result.get("content", ""))
                score = result.get("score", result.get("relevance_score", 0))

                # 형량 추출
                sentence = _extract_sentence_from_text(text)

                precedents.append({
                    "case_number": metadata.get("case_number", metadata.get("사건번호", "")),
                    "court": metadata.get("court", metadata.get("법원명", "")),
                    "date": metadata.get("decision_date", metadata.get("선고일자", "")),
                    "crime_type": crime_type,
                    "sentence": sentence,
                    "summary": text[:350] if text else "",
                    "relevance": round(score * 100, 1) if score <= 1 else round(score, 1),
                })

            logger.info(f"[search_precedents_node] Retrieved {len(results)} results, formatted {len(precedents)} precedents")

        except Exception as e:
            logger.warning(f"[search_precedents_node] Precedent search failed: {e}", exc_info=True)

        logger.info(f"[search_precedents_node] Found {len(precedents)} precedents")

        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "search_precedents"]

        return {
            "related_precedents": precedents,
            "precedents_status": "completed",
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["search_precedents"]
        }

    except Exception as e:
        logger.error(f"[search_precedents_node] Error: {e}", exc_info=True)
        plan = state.get("analysis_plan", [])
        new_plan = [p for p in plan if p != "search_precedents"]
        return {
            "related_precedents": [],
            "precedents_status": "failed",
            "analysis_plan": new_plan,
            "completed_tasks": state.get("completed_tasks", []) + ["search_precedents_failed"]
        }


def _extract_sentence_from_text(text: str) -> str:
    """판결문 텍스트에서 형량 정보 추출"""
    patterns = [
        r"징역\s*(\d+)\s*년",
        r"징역\s*(\d+)\s*월",
        r"금고\s*(\d+)\s*년",
        r"금고\s*(\d+)\s*월",
        r"벌금\s*(\d+[\d,]*)\s*원",
        r"집행유예\s*(\d+)\s*년",
        r"무죄",
    ]

    sentences = []
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            sentences.append(match.group(0))

    return ", ".join(sentences) if sentences else "형량 정보 없음"


async def generate_summary_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    사건 요약 생성 노드
    """
    logger.info("[generate_summary_node] Generating summary")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        texts = state.get("texts", [])
        filenames = state.get("filenames", [])
        combined_text = "\n\n".join(texts)[:8000]
        crime_type = state.get("crime_type", "미상")

        prompt = f"""다음 {crime_type} 사건 문서를 요약하세요.

파일: {', '.join(filenames)}

문서 내용:
{combined_text}

요약 가이드:
1. 사건 개요 (누가, 언제, 어디서, 무엇을)
2. 주요 혐의 및 범죄 사실
3. 피해 규모
4. 현재 진행 상황

3-5문장으로 요약하세요."""

        summary = llm_client.generate(prompt=prompt, temperature=0.2, max_tokens=500)

        # 기존 summary에 추가 (카테고리별 분석 결과가 있을 수 있음)
        existing_summary = state.get("summary") or ""
        full_summary = summary + existing_summary

        return {
            "summary": full_summary,
            "completed_tasks": state.get("completed_tasks", []) + ["generate_summary"]
        }

    except Exception as e:
        logger.error(f"[generate_summary_node] Error: {e}")
        return {
            "summary": f"요약 생성 실패: {str(e)}",
            "completed_tasks": state.get("completed_tasks", []) + ["generate_summary_failed"]
        }


async def aggregate_node(state: CriminalCaseState) -> Dict[str, Any]:
    """
    결과 집계 노드
    """
    logger.info("[aggregate_node] Aggregating results")

    completed_tasks = state.get("completed_tasks", [])

    if state.get("error"):
        logger.warning(f"[aggregate_node] Error found: {state.get('error')}")

    return {
        "completed_tasks": completed_tasks + ["aggregate"]
    }


# ============================================================================
# Workflow Graph Creation
# ============================================================================

def create_criminal_workflow() -> StateGraph:
    """
    Criminal Case Analysis Workflow 생성

    그래프 구조:
        START
          |
          v
      detect_crime
          |
          v
      plan_analysis
          |
          v
    [route_by_category]
      /    |    |    \
     v     v    v     v
  property violent traffic general
      \    |    |    /
       +---+----+---+
           |
           v
      generate_summary
           |
           v
     analyze_elements
           |
           v
     extract_factors
           |
           v
    estimate_sentence
           |
           v
     suggest_defense
           |
           v
    search_precedents
           |
           v
       aggregate
           |
           v
          END
    """
    workflow = StateGraph(CriminalCaseState)

    # 노드 추가
    workflow.add_node("detect_crime", detect_crime_node)
    workflow.add_node("plan_analysis", plan_analysis_node)
    workflow.add_node("analyze_property", analyze_property_crime_node)
    workflow.add_node("analyze_violent", analyze_violent_crime_node)
    workflow.add_node("analyze_traffic", analyze_traffic_crime_node)
    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("analyze_elements", analyze_elements_node)
    workflow.add_node("extract_factors", extract_factors_node)
    workflow.add_node("estimate_sentence", estimate_sentence_node)
    workflow.add_node("suggest_defense", suggest_defense_node)
    workflow.add_node("search_precedents", search_precedents_node)
    workflow.add_node("aggregate", aggregate_node)

    # 엣지 정의
    workflow.add_edge(START, "detect_crime")
    workflow.add_edge("detect_crime", "plan_analysis")

    # 조건부 분기
    workflow.add_conditional_edges(
        "plan_analysis",
        route_by_category,
        {
            "property": "analyze_property",
            "violent": "analyze_violent",
            "traffic": "analyze_traffic",
            "general": "generate_summary",
        }
    )

    # 카테고리별 분석 후 공통 흐름으로
    workflow.add_edge("analyze_property", "generate_summary")
    workflow.add_edge("analyze_violent", "generate_summary")
    workflow.add_edge("analyze_traffic", "generate_summary")

    # 공통 분석 흐름
    workflow.add_edge("generate_summary", "analyze_elements")
    workflow.add_edge("analyze_elements", "extract_factors")
    workflow.add_edge("extract_factors", "estimate_sentence")
    workflow.add_edge("estimate_sentence", "suggest_defense")

    # 조건부 분기: skip_precedents 여부에 따라 판례 검색 스킵
    workflow.add_conditional_edges(
        "suggest_defense",
        route_after_defense,
        {
            "search_precedents": "search_precedents",
            "aggregate": "aggregate"
        }
    )

    workflow.add_edge("search_precedents", "aggregate")
    workflow.add_edge("aggregate", END)

    return workflow.compile()


# ============================================================================
# Workflow Class (BaseWorkflow 상속)
# ============================================================================

class CriminalCaseWorkflow(BaseWorkflow[CriminalCaseState]):
    """
    Criminal Case Analysis Workflow 클래스

    사용:
        workflow = CriminalCaseWorkflow()
        result = await workflow.arun(
            texts=["문서 내용..."],
            filenames=["기소장.pdf"],
            user_id="user-123"
        )
    """

    def __init__(self):
        super().__init__(
            name="criminal_case_workflow",
            use_checkpointing=False,
            recursion_limit=30
        )

    def create_graph(self) -> StateGraph:
        """StateGraph 생성"""
        workflow = StateGraph(CriminalCaseState)

        # 노드 추가
        workflow.add_node("detect_crime", detect_crime_node)
        workflow.add_node("plan_analysis", plan_analysis_node)
        workflow.add_node("analyze_property", analyze_property_crime_node)
        workflow.add_node("analyze_violent", analyze_violent_crime_node)
        workflow.add_node("analyze_traffic", analyze_traffic_crime_node)
        workflow.add_node("generate_summary", generate_summary_node)
        workflow.add_node("analyze_elements", analyze_elements_node)
        workflow.add_node("extract_factors", extract_factors_node)
        workflow.add_node("estimate_sentence", estimate_sentence_node)
        workflow.add_node("suggest_defense", suggest_defense_node)
        workflow.add_node("search_precedents", search_precedents_node)
        workflow.add_node("aggregate", aggregate_node)

        # 엣지 정의
        workflow.add_edge(START, "detect_crime")
        workflow.add_edge("detect_crime", "plan_analysis")

        workflow.add_conditional_edges(
            "plan_analysis",
            route_by_category,
            {
                "property": "analyze_property",
                "violent": "analyze_violent",
                "traffic": "analyze_traffic",
                "general": "generate_summary",
            }
        )

        workflow.add_edge("analyze_property", "generate_summary")
        workflow.add_edge("analyze_violent", "generate_summary")
        workflow.add_edge("analyze_traffic", "generate_summary")

        workflow.add_edge("generate_summary", "analyze_elements")
        workflow.add_edge("analyze_elements", "extract_factors")
        workflow.add_edge("extract_factors", "estimate_sentence")
        workflow.add_edge("estimate_sentence", "suggest_defense")

        # 조건부 분기: skip_precedents 여부에 따라 판례 검색 스킵
        workflow.add_conditional_edges(
            "suggest_defense",
            route_after_defense,
            {
                "search_precedents": "search_precedents",
                "aggregate": "aggregate"
            }
        )

        workflow.add_edge("search_precedents", "aggregate")
        workflow.add_edge("aggregate", END)

        return workflow

    def create_initial_state(
        self,
        texts: List[str],
        filenames: List[str],
        user_id: Optional[str] = None,
        case_name: Optional[str] = None,
        crime_type: Optional[str] = None,
        skip_precedents: bool = False,
        **kwargs
    ) -> CriminalCaseState:
        """
        초기 상태 생성

        Args:
            texts: 문서 텍스트 리스트
            filenames: 파일명 리스트
            user_id: 사용자 ID
            case_name: 사건명 (선택)
            crime_type: 범죄 유형 (선택, 미지정시 자동 감지)
            skip_precedents: 판례 검색 스킵 여부 (True면 나중에 별도 API로 검색)

        Returns:
            초기 CriminalCaseState
        """
        return CriminalCaseState(
            texts=texts,
            filenames=filenames,
            user_id=user_id,
            case_name=case_name,
            input_crime_type=crime_type,
            summary=None,
            crime_type=None,
            crime_category=None,
            criminal_stage=None,
            crime_elements=None,
            sentencing_factors=None,
            expected_sentence=None,
            defense_strategies=[],
            related_precedents=[],
            analysis_plan=[],
            completed_tasks=[],
            error=None,
            skip_precedents=skip_precedents,
            precedents_status="pending" if skip_precedents else None,
        )

    def _format_result(
        self,
        result: Dict[str, Any],
        processing_time: float,
        session_id: str
    ) -> Dict[str, Any]:
        """결과 포맷팅"""
        return {
            "success": result.get("error") is None,
            "summary": result.get("summary"),
            "crime_type": result.get("crime_type"),
            "crime_category": result.get("crime_category"),
            "criminal_stage": result.get("criminal_stage", "COMPLAINT"),  # 형사 절차 단계
            "crime_elements": result.get("crime_elements"),
            "sentencing_factors": result.get("sentencing_factors"),
            "expected_sentence": result.get("expected_sentence"),
            "defense_strategies": result.get("defense_strategies", []),
            "related_precedents": result.get("related_precedents", []),
            "precedents_status": result.get("precedents_status"),  # 판례 검색 상태
            "completed_tasks": result.get("completed_tasks", []),
            "processing_time": processing_time,
            "session_id": session_id,
            "error": result.get("error"),
        }


# ============================================================================
# Factory Functions
# ============================================================================

def get_criminal_workflow() -> CriminalCaseWorkflow:
    """CriminalCaseWorkflow 인스턴스 반환"""
    return CriminalCaseWorkflow()

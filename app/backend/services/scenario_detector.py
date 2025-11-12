"""
시나리오 자동 감지 모듈
업로드된 문서와 분석 결과를 바탕으로 8가지 시나리오 중 적합한 것을 자동 판단
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ScenarioDetector:
    """시나리오 자동 감지 클래스"""

    # 8가지 시나리오 정의 (핵심 템플릿 6개로 축소)
    SCENARIOS = {
        "scenario_1_initial_consultation": {
            "name": "초기 상담 및 사건 접수",
            "description": "의뢰인이 처음 방문하여 각종 서류를 들고 왔을 때",
            "templates": []  # 초기 상담 단계에서는 문서 생성 불필요
        },
        "scenario_2_civil_plaintiff": {
            "name": "민사소송 - 원고 대리",
            "description": "돈을 받아야 하는 경우",
            "templates": ["소장"]
        },
        "scenario_3_civil_defendant": {
            "name": "민사소송 - 피고 대리",
            "description": "돈 달라는 소송을 당한 경우",
            "templates": ["답변서"]
        },
        "scenario_4_criminal_defense": {
            "name": "형사변호 - 피고인 변호",
            "description": "형사 기소당한 경우",
            "templates": ["변론요지서"]
        },
        "scenario_5_criminal_complaint": {
            "name": "형사 고소/고발",
            "description": "범죄 피해자",
            "templates": ["고소장"]
        },
        "scenario_6_contract_review": {
            "name": "계약서 검토/작성",
            "description": "계약서 서명 전 검토",
            "templates": ["근로계약서", "임대차계약서", "업무위탁계약서", "매매계약서"]
        },
        "scenario_7_demand_letter": {
            "name": "내용증명/경고장",
            "description": "소송 전 의사 전달",
            "templates": ["내용증명"]
        },
        "scenario_8_damages": {
            "name": "교통사고/손해배상",
            "description": "손해배상을 받아야 하는 경우",
            "templates": ["손해배상청구서"]
        }
    }

    @classmethod
    def detect_scenario(
        cls,
        analysis: Dict[str, Any],
        filenames: List[str]
    ) -> Dict[str, Any]:
        """
        분석 결과와 파일명을 기반으로 시나리오 자동 감지

        Args:
            analysis: AI 분석 결과
            filenames: 업로드된 파일명 리스트

        Returns:
            {
                "scenario_id": "scenario_2_civil_plaintiff",
                "scenario_name": "민사소송 - 원고 대리",
                "confidence": 0.85,
                "suggested_templates": ["소장", "준비서면_원고", "증거목록"]
            }
        """
        # 텍스트 결합 (분석 요약 + 파일명)
        combined_text = analysis.get("summary", "") + " " + " ".join(filenames)
        combined_text = combined_text.lower()

        # 문서 유형 추출
        doc_types = [t.lower() for t in analysis.get("document_types", [])]

        # 시나리오별 점수 계산
        scores = {}

        # Scenario 1: 초기 상담
        score_1 = 0
        if len(filenames) >= 2:  # 여러 파일 업로드
            score_1 += 0.3
        if not any(keyword in combined_text for keyword in ["소장", "판결", "기소", "고소"]):
            score_1 += 0.3  # 명확한 소송 단계 아님
        scores["scenario_1_initial_consultation"] = score_1

        # Scenario 2: 민사소송 - 원고
        score_2 = 0
        if "소장" in combined_text and "원고" in combined_text:
            score_2 += 0.5
        if any(keyword in combined_text for keyword in ["채권", "대여", "미지급", "손해배상"]):
            score_2 += 0.3
        if "피고" not in combined_text:  # 피고가 아님
            score_2 += 0.2
        scores["scenario_2_civil_plaintiff"] = score_2

        # Scenario 3: 민사소송 - 피고
        score_3 = 0
        if "소장" in combined_text and "피고" in combined_text:
            score_3 += 0.5
        if "답변서" in combined_text or "받은 소장" in combined_text:
            score_3 += 0.4
        if any(keyword in combined_text for keyword in ["상계", "항변", "부인"]):
            score_3 += 0.2
        scores["scenario_3_civil_defendant"] = score_3

        # Scenario 4: 형사변호
        score_4 = 0
        if any(keyword in combined_text for keyword in ["기소", "피고인", "형사", "약식명령"]):
            score_4 += 0.5
        if "검사" in combined_text or "경찰" in combined_text:
            score_4 += 0.2
        if any(keyword in combined_text for keyword in ["조서", "변호"]):
            score_4 += 0.3
        scores["scenario_4_criminal_defense"] = score_4

        # Scenario 5: 형사 고소
        score_5 = 0
        if any(keyword in combined_text for keyword in ["사기", "횡령", "절도", "피해"]):
            score_5 += 0.4
        if "고소" in combined_text or "고발" in combined_text:
            score_5 += 0.4
        if "피해자" in combined_text or "피의자" in combined_text:
            score_5 += 0.2
        scores["scenario_5_criminal_complaint"] = score_5

        # Scenario 6: 계약서 검토
        score_6 = 0
        if "계약서" in doc_types or "계약서" in combined_text:
            score_6 += 0.6
        # 특정 계약서 유형 키워드 체크
        contract_keywords = ["근로계약", "임대차", "전세", "월세", "업무위탁", "용역", "매매", "부동산"]
        if any(keyword in combined_text for keyword in contract_keywords):
            score_6 += 0.4
        if not any(keyword in combined_text for keyword in ["소장", "판결", "고소"]):
            score_6 += 0.3  # 소송 단계 아님
        if any(keyword in combined_text for keyword in ["검토", "서명", "체결", "작성"]):
            score_6 += 0.2
        scores["scenario_6_contract_review"] = score_6

        # Scenario 7: 내용증명
        score_7 = 0
        if "내용증명" in combined_text or "경고" in combined_text:
            score_7 += 0.5
        if any(keyword in combined_text for keyword in ["채무", "독촉", "이행최고"]):
            score_7 += 0.3
        if not any(keyword in combined_text for keyword in ["소장", "판결"]):
            score_7 += 0.2  # 아직 소송 전
        scores["scenario_7_demand_letter"] = score_7

        # Scenario 8: 손해배상
        score_8 = 0
        if any(keyword in combined_text for keyword in ["사고", "진단서", "의무기록"]):
            score_8 += 0.5
        if "교통사고" in combined_text or "의료사고" in combined_text:
            score_8 += 0.3
        if any(keyword in combined_text for keyword in ["치료", "수리", "보험"]):
            score_8 += 0.2
        scores["scenario_8_damages"] = score_8

        # 최고 점수 시나리오 선택
        if not scores or max(scores.values()) < 0.3:
            # 점수가 너무 낮으면 초기 상담으로 간주
            selected_scenario = "scenario_1_initial_consultation"
            confidence = 0.5
        else:
            selected_scenario = max(scores, key=scores.get)
            confidence = scores[selected_scenario]

        scenario_info = cls.SCENARIOS[selected_scenario]

        logger.info(f"Detected scenario: {selected_scenario} (confidence: {confidence:.2f})")
        logger.debug(f"All scores: {scores}")

        return {
            "scenario_id": selected_scenario,
            "scenario_name": scenario_info["name"],
            "scenario_description": scenario_info["description"],
            "confidence": round(confidence, 2),
            "suggested_templates": scenario_info["templates"]
        }

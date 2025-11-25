"""
Risk Analysis Service
리스크 분석 서비스
"""

from typing import Dict, Any, Optional, List
import logging
import json
import re

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """
    Contract/Document Risk Analyzer using LLM

    Identifies potential risks, red flags, and assigns risk scores including:
    - Legal risks
    - Financial risks
    - Compliance risks
    - Operational risks
    - Reputational risks
    """

    # Risk severity thresholds
    SEVERITY_THRESHOLDS = {
        "CRITICAL": 80,
        "HIGH": 60,
        "MEDIUM": 40,
        "LOW": 20,
        "INFO": 0
    }

    # Risk categories
    RISK_CATEGORIES = [
        "LEGAL",
        "FINANCIAL",
        "COMPLIANCE",
        "OPERATIONAL",
        "REPUTATIONAL",
        "OTHER"
    ]

    def __init__(self, llm_client):
        """
        Initialize RiskAnalyzer with LLM client

        Args:
            llm_client: LLM client instance (from libs.rag_core)
        """
        self.llm = llm_client

    async def analyze_risk(
        self,
        text: str,
        document_id: Optional[str] = None,
        document_type: str = "CONTRACT",
        llm_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze document for potential risks using LLM

        Args:
            text: Document text to analyze
            document_id: Optional document ID for reference
            document_type: Type of document (CONTRACT, STATUTE, etc.)
            llm_model: LLM model name (for metadata only)

        Returns:
            {
                "overall_risk_score": 75,
                "severity": "HIGH",
                "risk_items": [
                    {
                        "category": "LEGAL",
                        "title": "불명확한 계약 해지 조항",
                        "description": "계약 해지 사유가 구체적이지 않아...",
                        "severity": "HIGH",
                        "score": 80,
                        "clause_reference": "제5조"
                    },
                    ...
                ],
                "recommendations": [
                    "계약 해지 조항을 보다 구체적으로 명시할 것을 권장합니다.",
                    ...
                ],
                "summary": "전반적인 리스크 요약...",
                "meta": {
                    "token_count": 2000,
                    "risk_item_count": 5,
                    "model_version": "gpt-4"
                }
            }
        """
        try:
            # Validate input
            if not text or len(text.strip()) == 0:
                raise ValueError("Text cannot be empty")

            # Prepare prompt
            prompt = self._create_risk_analysis_prompt(text, document_type)

            # Call LLM
            logger.info(f"Analyzing risks for document {document_id}...")

            response = self.llm.generate(
                prompt=prompt,
                temperature=0.3,  # Low temperature for consistent analysis
                max_tokens=3000
            )

            # Parse response
            analysis = self._parse_risk_analysis(response)

            # Calculate overall risk score
            overall_score = self._calculate_overall_risk_score(analysis["risk_items"])
            severity = self._determine_severity(overall_score)

            # Prepare result
            result = {
                "overall_risk_score": overall_score,
                "severity": severity,
                "risk_items": analysis["risk_items"],
                "recommendations": analysis["recommendations"],
                "summary": analysis["summary"],
                "meta": {
                    "token_count": self._estimate_token_count(response),
                    "risk_item_count": len(analysis["risk_items"]),
                    "model_version": llm_model or "unknown"
                }
            }

            logger.info(
                f"Risk analysis completed for document {document_id}: "
                f"Score={overall_score}, Severity={severity}, Items={len(analysis['risk_items'])}"
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing risks: {e}", exc_info=True)
            raise

    def _create_risk_analysis_prompt(self, text: str, document_type: str) -> str:
        """
        Create prompt for risk analysis

        Args:
            text: Document text
            document_type: Type of document

        Returns:
            Formatted prompt string
        """
        prompt = f"""당신은 법률 리스크 분석 전문가입니다. 다음 {document_type} 문서를 분석하여 잠재적 리스크를 식별해주세요.

문서 내용:
{text}

다음 JSON 형식으로 리스크 분석 결과를 작성해주세요:

{{
  "risk_items": [
    {{
      "category": "LEGAL|FINANCIAL|COMPLIANCE|OPERATIONAL|REPUTATIONAL|OTHER",
      "title": "리스크 제목 (간결하게)",
      "description": "리스크 상세 설명 (구체적으로)",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "score": 0-100 (높을수록 위험),
      "clause_reference": "해당 조항 번호 (예: 제5조)"
    }}
  ],
  "recommendations": [
    "리스크 완화를 위한 구체적 권장사항 1",
    "리스크 완화를 위한 구체적 권장사항 2"
  ],
  "summary": "전반적인 리스크 분석 요약 (3-5문장)"
}}

리스크 분석 시 다음 사항에 중점을 두세요:
1. **법적 리스크 (LEGAL)**: 불명확한 조항, 일방적 조항, 법적 분쟁 가능성
2. **금융 리스크 (FINANCIAL)**: 과도한 위약금, 불리한 지급 조건, 금전적 손실 가능성
3. **컴플라이언스 리스크 (COMPLIANCE)**: 법규 위반 가능성, 규제 미준수
4. **운영 리스크 (OPERATIONAL)**: 이행 불가능한 의무, 과도한 책임
5. **평판 리스크 (REPUTATIONAL)**: 브랜드 손상 가능성, 정보 유출 위험

각 리스크 항목에 대해:
- 구체적이고 명확한 제목과 설명
- 적절한 심각도 (CRITICAL: 80-100, HIGH: 60-79, MEDIUM: 40-59, LOW: 20-39, INFO: 0-19)
- 실질적이고 실행 가능한 권장사항

반드시 올바른 JSON 형식으로만 응답해주세요."""

        return prompt

    def _parse_risk_analysis(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response for risk analysis

        Args:
            response: LLM response text

        Returns:
            Parsed risk analysis dict
        """
        try:
            # Try to parse as JSON first
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response

            parsed = json.loads(json_str)

            # Validate required fields
            risk_items = parsed.get("risk_items", [])
            recommendations = parsed.get("recommendations", [])
            summary = parsed.get("summary", "")

            # Ensure risk_items have all required fields
            for item in risk_items:
                if "category" not in item:
                    item["category"] = "OTHER"
                if "title" not in item:
                    item["title"] = "Unspecified Risk"
                if "description" not in item:
                    item["description"] = ""
                if "severity" not in item:
                    item["severity"] = "MEDIUM"
                if "score" not in item:
                    item["score"] = 50
                if "clause_reference" not in item:
                    item["clause_reference"] = ""

                # Normalize severity
                severity_upper = item["severity"].upper()
                if severity_upper not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                    item["severity"] = "MEDIUM"
                    item["score"] = 50
                else:
                    item["severity"] = severity_upper

                # Ensure score is in valid range
                item["score"] = max(0, min(100, int(item["score"])))

            return {
                "risk_items": risk_items,
                "recommendations": recommendations if isinstance(recommendations, list) else [],
                "summary": summary if summary else "리스크 분석이 완료되었습니다."
            }

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response, using fallback parsing")
            # Fallback: create basic structure
            return {
                "risk_items": [{
                    "category": "OTHER",
                    "title": "문서 분석 결과",
                    "description": response[:500],  # First 500 chars
                    "severity": "MEDIUM",
                    "score": 50,
                    "clause_reference": ""
                }],
                "recommendations": ["전문가의 상세 검토를 권장합니다."],
                "summary": "문서에 대한 리스크 분석이 수행되었습니다."
            }

    def _calculate_overall_risk_score(self, risk_items: List[Dict[str, Any]]) -> int:
        """
        Calculate overall risk score from individual risk items

        Args:
            risk_items: List of risk items with scores

        Returns:
            Overall risk score (0-100)
        """
        if not risk_items:
            return 0

        # Weighted average based on severity
        total_score = sum(item.get("score", 50) for item in risk_items)
        avg_score = total_score / len(risk_items)

        # Round to nearest integer
        return int(round(avg_score))

    def _determine_severity(self, score: int) -> str:
        """
        Determine severity level from score

        Args:
            score: Risk score (0-100)

        Returns:
            Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        """
        if score >= self.SEVERITY_THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        elif score >= self.SEVERITY_THRESHOLDS["HIGH"]:
            return "HIGH"
        elif score >= self.SEVERITY_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        elif score >= self.SEVERITY_THRESHOLDS["LOW"]:
            return "LOW"
        else:
            return "INFO"

    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text

        Simple estimation: ~1 token per 4 characters for Korean/English mixed text

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

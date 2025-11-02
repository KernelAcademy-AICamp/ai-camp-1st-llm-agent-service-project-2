"""
법률 문서 생성 서비스
템플릿과 AI를 활용하여 법률 문서 자동 생성
"""

from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """법률 문서 생성 클래스"""

    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM 클라이언트
        """
        self.llm = llm_client

    async def generate_document(
        self,
        template_name: str,
        case_analysis: Dict[str, Any],
        generation_mode: str = "quick",
        custom_fields: Optional[Dict[str, str]] = None,
        user_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        템플릿 기반 법률 문서 생성

        Args:
            template_name: 템플릿 이름 (예: "소장", "답변서")
            case_analysis: 사건 분석 결과
            generation_mode: 생성 모드 ("quick" 또는 "custom")
            custom_fields: 맞춤 생성 시 사용자 입력 필드
            user_instructions: 사용자 추가 지시사항

        Returns:
            {
                "title": "문서 제목",
                "content": "생성된 문서 내용",
                "template_used": "소장",
                "metadata": {...}
            }
        """
        try:
            # 템플릿별 프롬프트 생성
            prompt = self._build_prompt(
                template_name,
                case_analysis,
                generation_mode,
                custom_fields,
                user_instructions
            )

            # LLM으로 문서 생성
            logger.info(f"Generating document: {template_name}")
            generated_text = self.llm.generate(
                prompt=prompt,
                temperature=0.3,  # 법률 문서는 일관성 중요
                max_tokens=3000
            )

            # 메타데이터 추출
            metadata = self._extract_metadata(template_name, case_analysis)

            result = {
                "title": self._get_document_title(template_name, case_analysis),
                "content": generated_text,
                "template_used": template_name,
                "metadata": metadata
            }

            logger.info(f"Document generated successfully: {template_name}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate document {template_name}: {e}")
            raise

    def _build_prompt(
        self,
        template_name: str,
        case_analysis: Dict[str, Any],
        generation_mode: str,
        custom_fields: Optional[Dict[str, str]],
        user_instructions: Optional[str]
    ) -> str:
        """템플릿별 프롬프트 구성"""

        # 공통 사건 정보
        case_info = f"""
사건 정보:
- 사건명: {case_analysis.get('suggested_case_name', 'Unknown')}
- 요약: {case_analysis.get('summary', '')}
- 문서 유형: {', '.join(case_analysis.get('document_types', []))}
- 당사자: {json.dumps(case_analysis.get('parties', {}), ensure_ascii=False)}
- 주요 쟁점: {', '.join(case_analysis.get('issues', []))}
- 주요 날짜: {json.dumps(case_analysis.get('key_dates', {}), ensure_ascii=False)}
"""

        # 맞춤 생성 모드: 사용자 입력 필드 추가
        if generation_mode == "custom" and custom_fields:
            case_info += "\n사용자 입력 정보:\n"
            for field_name, field_value in custom_fields.items():
                if field_value:
                    # 필드명을 한글로 변환
                    field_labels = {
                        "claim_amount": "청구 금액",
                        "claim_purpose": "청구 취지",
                        "case_summary": "사건 개요",
                        "admission": "인정 사항",
                        "denial": "부인 사항",
                        "defense": "항변 내용",
                        "suspect_name": "피고소인 성명",
                        "suspect_info": "피고소인 정보",
                        "crime_fact": "범죄 사실",
                        "evidence_summary": "증거 개요",
                        "defense_argument": "변론 요지",
                        "evidence_critique": "검사 증거 반박",
                        "recipient_name": "수신인",
                        "debt_amount": "채무 금액",
                        "deadline": "이행 기한",
                        "legal_action": "불이행 시 조치"
                    }
                    label = field_labels.get(field_name, field_name)
                    case_info += f"- {label}: {field_value}\n"

        # 템플릿별 프롬프트
        prompts = {
            "소장": f"""당신은 대한민국 민사소송 전문 변호사입니다.
다음 사건 정보를 바탕으로 민사소송 소장을 작성해주세요.

{case_info}

소장 작성 형식:
1. 사건명
2. 당사자 표시
   - 원고: [이름, 주소, 주민등록번호]
   - 피고: [이름, 주소, 주민등록번호]
3. 청구 취지
   "피고는 원고에게 금 [금액]원 및 이에 대한 [날짜]부터 다 갚는 날까지 연 [%]의 비율로 계산한 지연손해금을 지급하라."
4. 청구 원인
   - 계약 체결 경위
   - 이행 내역
   - 불이행 사실
   - 손해 발생 및 인과관계
5. 증거 방법
6. 첨부 서류

전문적이고 정확한 법률 용어를 사용하여 작성해주세요.
""",
            "답변서": f"""당신은 대한민국 민사소송 전문 변호사입니다.
다음 사건 정보를 바탕으로 민사소송 답변서를 작성해주세요.

{case_info}

답변서 작성 형식:
1. 사건명
2. 당사자 표시
3. 원고 주장에 대한 답변
   - 인정하는 사실
   - 부인하는 사실 및 이유
4. 항변 사유
   - 소멸시효 항변
   - 상계 항변
   - 기타 항변
5. 입증 방법
6. 결론

피고에게 유리한 법리와 사실관계를 적극적으로 반영하여 작성해주세요.
""",
            "고소장": f"""당신은 대한민국 형사법 전문 변호사입니다.
다음 사건 정보를 바탕으로 고소장을 작성해주세요.

{case_info}

고소장 작성 형식:
1. 고소인
   - 성명, 주소, 연락처
2. 피고소인
   - 성명, 주소 (알고 있는 범위)
3. 고소 취지
   "피고소인을 [죄명]으로 처벌해 주시기 바랍니다."
4. 고소 이유
   - 사건 경위 (육하원칙)
   - 범죄 성립 요건
   - 증거 자료
5. 첨부 서류

명확하고 설득력 있게 작성해주세요.
""",
            "변론요지서": f"""당신은 대한민국 형사변호 전문 변호사입니다.
다음 사건 정보를 바탕으로 피고인 변론요지서를 작성해주세요.

{case_info}

변론요지서 작성 형식:
1. 사건명
2. 피고인 인적사항
3. 변론 요지
   - 무죄 주장 근거
   - 검사 증거 탄핵
   - 유리한 정황 강조
4. 법리적 주장
5. 양형 참작 사유 (예비적)
6. 결론

피고인의 무죄 또는 감형을 위한 강력한 논거를 제시해주세요.
""",
            "사건접수보고서": f"""당신은 대한민국 로펌의 선임 변호사입니다.
다음 사건 정보를 바탕으로 사건접수보고서를 작성해주세요.

{case_info}

보고서 형식:
1. 의뢰인 정보
2. 사건 개요 (5W1H)
3. 제출된 증거 목록
4. 초기 법률 검토 의견
   - 법적 쟁점
   - 승소 가능성 평가
   - 예상 소송 전략
5. 예상 일정 및 비용
6. 제안 사항

체계적이고 전문적으로 작성해주세요.
""",
            "계약서검토의견서": f"""당신은 대한민국 계약법 전문 변호사입니다.
다음 계약서 정보를 바탕으로 검토 의견서를 작성해주세요.

{case_info}

의견서 형식:
1. 전체 평가 (서명 가능/불가)
2. 조항별 위험도 분석
   - 조항 번호
   - 문제점
   - 위험도 (상/중/하)
   - 수정 권고안
3. 특별히 주의할 조항
4. 추가 협상 제안 사항
5. 결론 및 권고사항

의뢰인의 이익을 보호하는 관점에서 작성해주세요.
""",
            "내용증명": f"""당신은 대한민국 민사법 전문 변호사입니다.
다음 사건 정보를 바탕으로 내용증명을 작성해주세요.

{case_info}

내용증명 형식:
1. 제목: "채무 이행 최고의 건"
2. 수신인
3. 발신인
4. 본문
   - 채권 발생 경위
   - 현재 미지급액
   - 이행 기한 (통상 7일)
   - 불이행 시 법적 조치 예고
5. 날짜

정중하면서도 단호한 어조로 작성해주세요.
""",
            "손해배상청구서": f"""당신은 대한민국 손해배상 전문 변호사입니다.
다음 사건 정보를 바탕으로 손해배상청구서를 작성해주세요.

{case_info}

청구서 형식:
1. 청구인/피청구인 정보
2. 사고 경위
3. 과실 비율
4. 손해액 산정
   - 치료비
   - 휴업손해
   - 수리비
   - 위자료
   - 합계
5. 산정 근거 (판례, 기준)
6. 증빙 자료 목록
7. 결론

법원 실무와 판례 기준에 맞춰 정확하게 작성해주세요.
"""
        }

        # 기본 프롬프트 (템플릿이 없는 경우)
        base_prompt = f"""당신은 대한민국 법률 전문가입니다.
다음 사건 정보를 바탕으로 {template_name} 문서를 작성해주세요.

{case_info}

전문적이고 정확한 법률 용어를 사용하여 작성해주세요.
"""

        prompt = prompts.get(template_name, base_prompt)

        # 사용자 추가 지시사항 반영
        if user_instructions:
            prompt += f"\n\n추가 요청사항:\n{user_instructions}"

        return prompt

    def _get_document_title(self, template_name: str, case_analysis: Dict[str, Any]) -> str:
        """문서 제목 생성"""
        case_name = case_analysis.get("suggested_case_name", "Unknown")
        return f"{template_name} - {case_name}"

    def _extract_metadata(self, template_name: str, case_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """문서 메타데이터 추출"""
        return {
            "template": template_name,
            "case_id": case_analysis.get("case_id", ""),
            "parties": case_analysis.get("parties", {}),
            "document_types": case_analysis.get("document_types", []),
            "issues": case_analysis.get("issues", [])
        }

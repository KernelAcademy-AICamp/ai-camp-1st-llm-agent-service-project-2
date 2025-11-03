"""
법률 문서 생성 서비스
템플릿 파일 기반 변수 치환 방식으로 문서 생성
"""

from typing import Dict, Any, Optional
import logging
import os
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """법률 문서 생성 클래스 - 템플릿 기반"""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM 클라이언트 (선택적, 빈 필드 채우기용)
        """
        self.llm = llm_client
        self.templates_dir = Path(__file__).parent.parent / "templates"

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
            user_instructions: 사용자 추가 지시사항 (미사용)

        Returns:
            {
                "title": "문서 제목",
                "content": "생성된 문서 내용",
                "template_used": "소장",
                "metadata": {...}
            }
        """
        try:
            # 1. 템플릿 파일 로드
            template_content = self._load_template(template_name)

            # 2. 변수 매핑 딕셔너리 생성
            variables = self._prepare_variables(
                case_analysis,
                custom_fields or {},
                generation_mode
            )

            # 3. 템플릿에 변수 치환
            document_content = self._fill_template(template_content, variables)

            # 4. 메타데이터 추출
            metadata = self._extract_metadata(template_name, case_analysis)

            result = {
                "title": self._get_document_title(template_name, case_analysis),
                "content": document_content,
                "template_used": template_name,
                "metadata": metadata
            }

            logger.info(f"Document generated successfully: {template_name}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate document {template_name}: {e}")
            raise

    def _load_template(self, template_name: str) -> str:
        """템플릿 파일 로드"""
        template_path = self.templates_dir / f"{template_name}.txt"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _prepare_variables(
        self,
        case_analysis: Dict[str, Any],
        custom_fields: Dict[str, str],
        generation_mode: str
    ) -> Dict[str, str]:
        """변수 딕셔너리 준비"""

        variables = {}

        # 현재 날짜
        variables['current_date'] = datetime.now().strftime("%Y년 %m월 %d일")

        # 사건명
        variables['case_name'] = custom_fields.get('case_name') or \
                                 case_analysis.get('suggested_case_name', '미정')

        # 당사자 정보 (공통 필드)
        parties = case_analysis.get('parties', {})

        # 원고/고소인/청구인 정보
        variables['plaintiff_name'] = custom_fields.get('plaintiff_name') or \
                                       parties.get('plaintiff', {}).get('name', '___________')
        variables['plaintiff_address'] = custom_fields.get('plaintiff_address') or \
                                          parties.get('plaintiff', {}).get('address', '___________')
        variables['plaintiff_contact'] = custom_fields.get('plaintiff_contact') or \
                                          parties.get('plaintiff', {}).get('contact', '___________')

        # 피고/피고소인/피청구인 정보
        variables['defendant_name'] = custom_fields.get('defendant_name') or \
                                       parties.get('defendant', {}).get('name', '___________')
        variables['defendant_address'] = custom_fields.get('defendant_address') or \
                                          parties.get('defendant', {}).get('address', '___________')
        variables['defendant_contact'] = custom_fields.get('defendant_contact') or \
                                          parties.get('defendant', {}).get('contact', '___________')

        # 법원/검찰 정보
        variables['court_name'] = custom_fields.get('court_name') or '서울중앙지방법원'
        variables['prosecutor_office'] = custom_fields.get('prosecutor_office') or '검찰청'

        # 변호사 정보 (해당 시)
        variables['lawyer_name'] = custom_fields.get('lawyer_name') or '변호사 ___________'

        # 템플릿별 특화 필드

        # 소장 관련
        variables['claim_amount'] = self._format_amount(custom_fields.get('claim_amount', ''))
        variables['claim_purpose'] = custom_fields.get('claim_purpose', '피고는 원고에게 금 ___________원을 지급하라.')
        variables['claim_reason'] = custom_fields.get('claim_reason', '약정된 채무를 이행하지 않고 있습니다.')
        variables['case_summary'] = custom_fields.get('case_summary') or \
                                     case_analysis.get('summary', '(상세 내역 기재)')

        # 답변서 관련
        variables['admission'] = custom_fields.get('admission', '(인정 사항 기재)')
        variables['denial'] = custom_fields.get('denial', '(부인 사항 및 이유 기재)')
        variables['defense'] = custom_fields.get('defense', '(항변 내용 기재)')

        # 고소장 관련
        variables['suspect_name'] = custom_fields.get('suspect_name', '___________')
        variables['suspect_info'] = custom_fields.get('suspect_info', '생년월일 및 주소 불상')
        variables['crime_type'] = custom_fields.get('crime_type', '사기')
        variables['crime_fact'] = custom_fields.get('crime_fact', '(범죄 사실 육하원칙에 따라 기재)')

        # 변론요지서 관련
        variables['defense_argument'] = custom_fields.get('defense_argument', '(변론 요지 기재)')
        variables['evidence_critique'] = custom_fields.get('evidence_critique', '(검사 증거 반박 내용)')
        variables['legal_argument'] = custom_fields.get('legal_argument', '(법리적 주장)')
        variables['sentencing_factors'] = custom_fields.get('sentencing_factors', '(양형 참작 사유)')

        # 내용증명 관련
        variables['recipient_name'] = custom_fields.get('recipient_name', '___________')
        variables['recipient_address'] = custom_fields.get('recipient_address', '___________')
        variables['document_title'] = custom_fields.get('document_title', '채무 이행 최고의 건')
        variables['debt_amount'] = self._format_amount(custom_fields.get('debt_amount', ''))
        variables['debt_origin'] = custom_fields.get('debt_origin', '(채권 발생 경위 기재)')
        variables['deadline'] = custom_fields.get('deadline', '7일 이내')
        variables['bank_account'] = custom_fields.get('bank_account', '(은행명) (계좌번호)')
        variables['legal_action'] = custom_fields.get('legal_action', '민사소송 제기')

        # 손해배상청구서 관련
        variables['accident_date'] = custom_fields.get('accident_date', '___________')
        variables['accident_location'] = custom_fields.get('accident_location', '___________')
        variables['accident_description'] = custom_fields.get('accident_description', '(사고 상세 경위 기재)')
        variables['liability_description'] = custom_fields.get('liability_description', '(과실 및 책임 관계 기재)')
        variables['damages_amount'] = self._format_amount(custom_fields.get('damages_amount', ''))
        variables['damages_breakdown'] = custom_fields.get('damages_breakdown', '(손해 내역 상세 기재)')
        variables['damages_calculation'] = custom_fields.get('damages_calculation', '(산정 근거 및 판례 기재)')

        # 공통 필드
        variables['evidence_list'] = custom_fields.get('evidence_list', '1. 증거자료 1\n2. 증거자료 2')
        variables['evidence_summary'] = custom_fields.get('evidence_summary', '(증거 개요 기재)')
        variables['additional_documents'] = custom_fields.get('additional_documents', '')

        return variables

    def _fill_template(self, template_content: str, variables: Dict[str, str]) -> str:
        """템플릿에 변수 치환"""
        result = template_content

        # {{variable_name}} 형식의 플레이스홀더를 치환
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

        # 치환되지 않은 플레이스홀더 확인 및 로깅
        remaining_placeholders = re.findall(r'\{\{(\w+)\}\}', result)
        if remaining_placeholders:
            logger.warning(f"Unfilled placeholders: {remaining_placeholders}")

        return result

    def _format_amount(self, amount: str) -> str:
        """금액 포맷팅"""
        if not amount:
            return '___________'

        try:
            # 숫자로 변환 후 천단위 콤마
            amount_int = int(amount)
            return f"{amount_int:,}"
        except (ValueError, TypeError):
            return amount

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

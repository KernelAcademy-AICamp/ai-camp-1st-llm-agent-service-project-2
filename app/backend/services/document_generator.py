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
        """변수 딕셔너리 준비 - 템플릿별 맞춤 매핑"""

        variables = {}

        # 현재 날짜
        variables['current_date'] = datetime.now().strftime("%Y년 %m월 %d일")

        # 사건명
        variables['case_name'] = custom_fields.get('case_name') or \
                                 case_analysis.get('suggested_case_name', '미정')

        # 당사자 정보 추출 - 한글/영문 키 모두 지원, 문자열/객체 모두 지원
        parties = case_analysis.get('parties', {})

        # Helper function to extract party info
        def extract_party_info(party_keys: list) -> tuple:
            """당사자 정보 추출 (여러 키 시도, 문자열/객체 모두 지원)"""
            for key in party_keys:
                party_info = parties.get(key)
                if party_info:
                    if isinstance(party_info, dict):
                        return party_info.get('name', '___________'), party_info.get('address', '___________'), party_info.get('contact', '___________')
                    elif isinstance(party_info, str):
                        return party_info, '___________', '___________'
            return '___________', '___________', '___________'

        # 원고/고소인 정보
        plaintiff_name, plaintiff_address, plaintiff_contact = extract_party_info(['원고', 'plaintiff', '고소인'])
        variables['plaintiff_name'] = custom_fields.get('plaintiff_name') or plaintiff_name
        variables['plaintiff_address'] = custom_fields.get('plaintiff_address') or plaintiff_address
        variables['plaintiff_contact'] = custom_fields.get('plaintiff_contact') or plaintiff_contact

        # 피고/피고인 정보
        defendant_name, defendant_address, defendant_contact = extract_party_info(['피고', 'defendant', '피고인'])
        variables['defendant_name'] = custom_fields.get('defendant_name') or defendant_name
        variables['defendant_address'] = custom_fields.get('defendant_address') or defendant_address
        variables['defendant_contact'] = custom_fields.get('defendant_contact') or defendant_contact

        # 피고소인 정보 (고소장용)
        suspect_name, suspect_address, suspect_contact = extract_party_info(['피고소인', 'suspect'])
        variables['suspect_name'] = custom_fields.get('suspect_name') or suspect_name
        variables['suspect_info'] = custom_fields.get('suspect_info') or \
                                     (f'주소: {suspect_address}' if suspect_address != '___________' else '생년월일 및 주소 불상')

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

        # 근로계약서 관련
        variables['contract_start_date'] = custom_fields.get('contract_start_date', '___________')
        variables['contract_end_date'] = custom_fields.get('contract_end_date', '___________')
        variables['workplace'] = custom_fields.get('workplace', '___________')
        variables['job_description'] = custom_fields.get('job_description', '___________')
        variables['work_start_time'] = custom_fields.get('work_start_time', '09:00')
        variables['work_end_time'] = custom_fields.get('work_end_time', '18:00')
        variables['break_time'] = custom_fields.get('break_time', '12:00 ~ 13:00')
        variables['work_days'] = custom_fields.get('work_days', '월요일부터 금요일까지')
        variables['rest_day'] = custom_fields.get('rest_day', '주 1회 (일요일)')
        variables['monthly_salary'] = self._format_amount(custom_fields.get('monthly_salary', ''))
        variables['payment_date'] = custom_fields.get('payment_date', '매월 말일')
        variables['payment_method'] = custom_fields.get('payment_method', '계좌 입금')
        variables['termination_notice_period'] = custom_fields.get('termination_notice_period', '30일')
        variables['employee_name'] = custom_fields.get('employee_name', '___________')
        variables['employee_id'] = custom_fields.get('employee_id', '___________')
        variables['employee_address'] = custom_fields.get('employee_address', '___________')
        variables['employer_company'] = custom_fields.get('employer_company', '___________')
        variables['employer_name'] = custom_fields.get('employer_name', '___________')
        variables['employer_business_number'] = custom_fields.get('employer_business_number', '___________')
        variables['employer_address'] = custom_fields.get('employer_address', '___________')

        # 임대차계약서 관련
        variables['property_address'] = custom_fields.get('property_address', '___________')
        variables['property_type'] = custom_fields.get('property_type', '___________')
        variables['property_area'] = custom_fields.get('property_area', '___________')
        variables['property_usage'] = custom_fields.get('property_usage', '주거용')
        variables['deposit_amount'] = self._format_amount(custom_fields.get('deposit_amount', ''))
        variables['monthly_rent'] = self._format_amount(custom_fields.get('monthly_rent', ''))
        variables['rent_payment_date'] = custom_fields.get('rent_payment_date', '매월 1일')
        variables['down_payment'] = self._format_amount(custom_fields.get('down_payment', ''))
        variables['interim_payment'] = self._format_amount(custom_fields.get('interim_payment', ''))
        variables['interim_payment_date'] = custom_fields.get('interim_payment_date', '___________')
        variables['balance_payment'] = self._format_amount(custom_fields.get('balance_payment', ''))
        variables['balance_payment_date'] = custom_fields.get('balance_payment_date', '___________')
        variables['property_delivery_date'] = custom_fields.get('property_delivery_date', '___________')
        variables['rent_delay_period'] = custom_fields.get('rent_delay_period', '2개월')
        variables['utility_responsibility'] = custom_fields.get('utility_responsibility', '임차인')
        variables['renewal_notice_period'] = custom_fields.get('renewal_notice_period', '2개월')
        variables['renewal_period'] = custom_fields.get('renewal_period', '2년간')
        variables['deposit_return_date'] = custom_fields.get('deposit_return_date', '명도일로부터 7일 이내')
        variables['landlord_name'] = custom_fields.get('landlord_name', '___________')
        variables['landlord_id'] = custom_fields.get('landlord_id', '___________')
        variables['landlord_address'] = custom_fields.get('landlord_address', '___________')
        variables['landlord_phone'] = custom_fields.get('landlord_phone', '___________')
        variables['tenant_name'] = custom_fields.get('tenant_name', '___________')
        variables['tenant_id'] = custom_fields.get('tenant_id', '___________')
        variables['tenant_address'] = custom_fields.get('tenant_address', '___________')
        variables['tenant_phone'] = custom_fields.get('tenant_phone', '___________')

        # 업무위탁계약서 관련
        variables['service_description'] = custom_fields.get('service_description', '___________')
        variables['work_scope'] = custom_fields.get('work_scope', '___________')
        variables['work_location'] = custom_fields.get('work_location', '___________')
        variables['report_frequency'] = custom_fields.get('report_frequency', '매주')
        variables['total_fee'] = self._format_amount(custom_fields.get('total_fee', ''))
        variables['payment_schedule'] = custom_fields.get('payment_schedule', '___________')
        variables['expense_responsibility'] = custom_fields.get('expense_responsibility', '수탁자')
        variables['delivery_date'] = custom_fields.get('delivery_date', '___________')
        variables['inspection_period'] = custom_fields.get('inspection_period', '7일')
        variables['warranty_period'] = custom_fields.get('warranty_period', '3개월')
        variables['ip_ownership'] = custom_fields.get('ip_ownership', '위탁자')
        variables['confidentiality_period'] = custom_fields.get('confidentiality_period', '3년')
        variables['late_payment_interest'] = custom_fields.get('late_payment_interest', '6')
        variables['cure_period'] = custom_fields.get('cure_period', '14일')
        variables['jurisdiction'] = custom_fields.get('jurisdiction', '서울중앙지방법원')
        variables['client_name'] = custom_fields.get('client_name', '___________')
        variables['client_representative'] = custom_fields.get('client_representative', '___________')
        variables['client_business_number'] = custom_fields.get('client_business_number', '___________')
        variables['client_address'] = custom_fields.get('client_address', '___________')
        variables['client_phone'] = custom_fields.get('client_phone', '___________')
        variables['contractor_name'] = custom_fields.get('contractor_name', '___________')
        variables['contractor_representative'] = custom_fields.get('contractor_representative', '___________')
        variables['contractor_business_number'] = custom_fields.get('contractor_business_number', '___________')
        variables['contractor_address'] = custom_fields.get('contractor_address', '___________')
        variables['contractor_phone'] = custom_fields.get('contractor_phone', '___________')

        # 매매계약서 관련
        variables['land_category'] = custom_fields.get('land_category', '___________')
        variables['building_structure'] = custom_fields.get('building_structure', '___________')
        variables['building_usage'] = custom_fields.get('building_usage', '___________')
        variables['total_price'] = self._format_amount(custom_fields.get('total_price', ''))
        variables['existing_encumbrance'] = custom_fields.get('existing_encumbrance', '근저당권')
        variables['defect_liability_period'] = custom_fields.get('defect_liability_period', '6개월')
        variables['loan_amount'] = self._format_amount(custom_fields.get('loan_amount', ''))
        variables['loan_approval_date'] = custom_fields.get('loan_approval_date', '___________')
        variables['refund_period'] = custom_fields.get('refund_period', '3일')
        variables['broker_name'] = custom_fields.get('broker_name', '___________')
        variables['broker_office'] = custom_fields.get('broker_office', '___________')
        variables['broker_address'] = custom_fields.get('broker_address', '___________')
        variables['broker_license'] = custom_fields.get('broker_license', '___________')
        variables['broker_phone'] = custom_fields.get('broker_phone', '___________')
        variables['seller_name'] = custom_fields.get('seller_name', '___________')
        variables['seller_id'] = custom_fields.get('seller_id', '___________')
        variables['seller_address'] = custom_fields.get('seller_address', '___________')
        variables['seller_phone'] = custom_fields.get('seller_phone', '___________')
        variables['buyer_name'] = custom_fields.get('buyer_name', '___________')
        variables['buyer_id'] = custom_fields.get('buyer_id', '___________')
        variables['buyer_address'] = custom_fields.get('buyer_address', '___________')
        variables['buyer_phone'] = custom_fields.get('buyer_phone', '___________')

        # 공통 계약 필드
        variables['contract_date'] = custom_fields.get('contract_date', datetime.now().strftime("%Y년 %m월 %d일"))
        variables['additional_terms'] = custom_fields.get('additional_terms', '(특약사항 없음)')

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

"""
PII Masking Service - 복원 가능한 마스킹

OpenAI API 호출 시 개인정보가 외부로 전송되지 않도록 마스킹하고,
응답 후 원본으로 복원하는 서비스입니다.

사용 방법:
    masker = PIIMasker(mode="legal")  # 법률 문서 분석에 권장

    # 마스킹
    masked_text, mapping = masker.mask(original_text)

    # LLM 호출 (마스킹된 텍스트로)
    response = llm.generate(masked_text)

    # 복원
    restored_response = masker.restore(response, mapping)

모드:
    - "fast": Presidio만 사용 (주민번호, 전화번호, 이메일, 계좌번호, 사업자번호)
    - "balanced": Presidio + 로컬 LLM (이름, 주소까지 마스킹)
    - "legal": 법률 문서 최적화 (필수 PII만 마스킹, 이름/주소 유지) ← 권장

모드별 마스킹 항목:
    | 항목        | fast | balanced | legal |
    |------------|------|----------|-------|
    | 주민번호    | ✅   | ✅       | ✅    |
    | 전화번호    | ✅   | ✅       | ✅    |
    | 이메일      | ✅   | ✅       | ✅    |
    | 계좌번호    | ✅   | ✅       | ✅    |
    | 사업자번호  | ✅   | ✅       | ✅    |
    | 이름        | ❌   | ✅       | ❌    |
    | 주소        | ❌   | ✅       | ❌    |

legal 모드 선택 이유:
    - 이름/주소를 마스킹하면 LLM이 당사자 관계, 지역별 법률 적용 등을 파악하기 어려움
    - 이름/주소는 유출되어도 주민번호/계좌번호 대비 즉각적 피해가 적음
    - 법률 문서에서 "임대인 [NAME_1]"보다 "임대인 김철수"가 문맥 파악에 유리
"""

import os
import re
import logging
import time
import uuid
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Presidio
try:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

# OpenAI (로컬 LLM 호출용)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class MaskingMode(str, Enum):
    """마스킹 모드"""
    FAST = "fast"          # Presidio만 (빠름, 패턴 기반만)
    BALANCED = "balanced"  # Presidio + 로컬 LLM (이름/주소까지)
    LEGAL = "legal"        # 법률 문서 최적화 (필수 PII만, 이름/주소 유지)


@dataclass
class MaskingResult:
    """마스킹 결과"""
    masked_text: str
    mapping: Dict[str, str]  # {placeholder: original_value}
    detected_entities: Dict[str, List[str]]  # {entity_type: [values]}
    processing_time: float
    mode: str


@dataclass
class PIIEntity:
    """감지된 PII 엔티티"""
    entity_type: str
    original_value: str
    placeholder: str
    start: int
    end: int
    score: float = 0.0


class PIIMasker:
    """
    복원 가능한 PII 마스킹 서비스

    특징:
    - 마스킹 후 원본 복원 가능 (매핑 유지)
    - Presidio 기반 패턴 매칭 (주민번호, 전화번호, 이메일, 계좌번호)
    - 로컬 LLM으로 이름/주소 추가 감지 (balanced 모드)
    - 로컬 LLM 우선 사용 (데이터 보안)
    """

    # 엔티티 타입별 플레이스홀더 접두사
    PLACEHOLDER_PREFIX = {
        "KR_RRN": "RRN",           # 주민등록번호
        "KR_PHONE": "PHONE",       # 전화번호
        "EMAIL_ADDRESS": "EMAIL",  # 이메일
        "KR_ACCOUNT": "ACCOUNT",   # 계좌번호
        "KR_BRN": "BRN",           # 사업자등록번호
        "PERSON_NAME": "NAME",     # 이름
        "ADDRESS": "ADDR",         # 주소
    }

    def __init__(
        self,
        mode: str = "balanced",
        llm_base_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
    ):
        """
        PIIMasker 초기화

        Args:
            mode: 마스킹 모드 ("fast" 또는 "balanced")
            llm_base_url: 로컬 LLM 서버 URL (None이면 환경변수에서 읽음)
            llm_api_key: LLM API 키 (로컬 LLM은 보통 필요 없음)
            llm_model: LLM 모델명
        """
        if not PRESIDIO_AVAILABLE:
            raise ImportError("presidio-analyzer and presidio-anonymizer are required. Run: pip install presidio-analyzer presidio-anonymizer")

        self.mode = MaskingMode(mode)
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

        # 한국어 패턴 인식기 추가
        self._add_korean_recognizers()

        # LLM 클라이언트 설정 (balanced 모드에서만 사용)
        # legal 모드는 패턴 기반만 사용 (이름/주소 마스킹 안 함)
        self.llm_client = None
        self.llm_model = None

        if self.mode == MaskingMode.BALANCED:
            self._setup_llm_client(llm_base_url, llm_api_key, llm_model)

        # 플레이스홀더 카운터 (세션별 고유성 보장)
        self._placeholder_counters: Dict[str, int] = {}

        logger.info(f"PIIMasker initialized: mode={self.mode.value}, llm_available={self.llm_client is not None}")

    def _add_korean_recognizers(self):
        """한국어 PII 패턴 인식기 추가"""

        # 주민등록번호 (다양한 형식)
        korean_rrn = PatternRecognizer(
            supported_entity="KR_RRN",
            patterns=[
                Pattern(name="RRN with hyphen", regex=r"\d{6}-\d{7}", score=0.95),
                Pattern(name="RRN no hyphen", regex=r"(?<!\d)\d{13}(?!\d)", score=0.85),
                Pattern(name="RRN with space", regex=r"\d{6}\s+-?\s*\d{7}", score=0.8),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_rrn)

        # 한국 전화번호 (다양한 형식)
        korean_phone = PatternRecognizer(
            supported_entity="KR_PHONE",
            patterns=[
                Pattern(name="Mobile with hyphen", regex=r"01[016789]-\d{3,4}-\d{4}", score=0.95),
                Pattern(name="Landline with hyphen", regex=r"0\d{1,2}-\d{3,4}-\d{4}", score=0.9),
                Pattern(name="Phone with space", regex=r"01[016789]\s+\d{3,4}\s+\d{4}", score=0.85),
                Pattern(name="Phone no separator", regex=r"(?<!\d)01[016789]\d{7,8}(?!\d)", score=0.75),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_phone)

        # 계좌번호 (하이픈 있는 형식만 - 하이픈 없는 건 오탐이 많음)
        korean_account = PatternRecognizer(
            supported_entity="KR_ACCOUNT",
            patterns=[
                # 은행 계좌번호 형식: 3-4자리-2-6자리-6-10자리
                Pattern(name="Account with hyphen", regex=r"\d{3,4}-\d{2,6}-\d{6,10}", score=0.85),
                # 카드번호 형식: 4-4-4-4
                Pattern(name="Card number", regex=r"\d{4}-\d{4}-\d{4}-\d{4}", score=0.9),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_account)

        # 사업자등록번호
        korean_brn = PatternRecognizer(
            supported_entity="KR_BRN",
            patterns=[
                Pattern(name="BRN with hyphen", regex=r"\d{3}-\d{2}-\d{5}", score=0.9),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_brn)

    def _setup_llm_client(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """로컬 LLM 클라이언트 설정"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not installed. LLM enhancement disabled.")
            return

        # 환경변수에서 설정 읽기 (우선순위: 파라미터 > LOCAL_LLM_* > LLM_*)
        # LOCAL_LLM_URL 또는 LOCAL_LLM_BASE_URL 모두 지원
        final_base_url = (
            base_url or
            os.getenv("LOCAL_LLM_BASE_URL") or
            os.getenv("LOCAL_LLM_URL") or
            os.getenv("LLM_BASE_URL")
        )
        final_api_key = api_key or os.getenv("LOCAL_LLM_API_KEY") or os.getenv("LLM_API_KEY") or "not-needed"
        final_model = model or os.getenv("LOCAL_LLM_MODEL") or os.getenv("LLM_MODEL") or "gpt-4o-mini"

        if final_base_url:
            # 로컬 LLM 사용
            logger.info(f"Using Local LLM at {final_base_url} with model {final_model}")
            self.llm_client = OpenAI(base_url=final_base_url, api_key=final_api_key)
            self.llm_model = final_model
        elif os.getenv("OPENAI_API_KEY"):
            # OpenAI 사용 (주의: 프로덕션에서는 권장하지 않음)
            logger.warning("Using OpenAI API for PII masking. Consider using local LLM for production.")
            self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.llm_model = final_model
        else:
            logger.warning("No LLM configuration found. Running in fast mode (Presidio only).")
            self.mode = MaskingMode.FAST

    def _get_next_placeholder(self, entity_type: str) -> str:
        """다음 플레이스홀더 생성"""
        prefix = self.PLACEHOLDER_PREFIX.get(entity_type, entity_type)
        if prefix not in self._placeholder_counters:
            self._placeholder_counters[prefix] = 0
        self._placeholder_counters[prefix] += 1
        return f"[{prefix}_{self._placeholder_counters[prefix]}]"

    def _reset_counters(self):
        """플레이스홀더 카운터 초기화"""
        self._placeholder_counters = {}

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        텍스트 마스킹 (복원 가능)

        Args:
            text: 마스킹할 텍스트

        Returns:
            (masked_text, mapping) - 마스킹된 텍스트와 복원용 매핑
        """
        start_time = time.time()
        self._reset_counters()

        mapping: Dict[str, str] = {}
        entities: List[PIIEntity] = []

        # 1단계: Presidio 패턴 기반 감지
        analyzer_results = self.analyzer.analyze(
            text=text,
            language="en",  # 패턴 기반이라 언어 무관
            entities=["KR_RRN", "KR_PHONE", "EMAIL_ADDRESS", "KR_ACCOUNT", "KR_BRN"]
        )

        # 감지된 엔티티를 PIIEntity로 변환
        for result in analyzer_results:
            original_value = text[result.start:result.end]
            placeholder = self._get_next_placeholder(result.entity_type)
            entities.append(PIIEntity(
                entity_type=result.entity_type,
                original_value=original_value,
                placeholder=placeholder,
                start=result.start,
                end=result.end,
                score=result.score,
            ))

        # 2단계: LLM 기반 추가 감지 (balanced 모드)
        if self.mode == MaskingMode.BALANCED and self.llm_client:
            try:
                llm_entities = self._llm_detect_pii(text, entities)
                entities.extend(llm_entities)
            except Exception as e:
                logger.error(f"LLM PII detection failed: {e}")

        # 3단계: 마스킹 적용 (뒤에서부터 치환하여 인덱스 유지)
        masked_text = text
        # 위치 기준 내림차순 정렬 (뒤에서부터 치환)
        sorted_entities = sorted(entities, key=lambda x: x.start, reverse=True)

        # 중복 제거 (같은 위치에 여러 엔티티가 있을 수 있음)
        seen_positions = set()
        unique_entities = []
        for entity in sorted_entities:
            pos_key = (entity.start, entity.end)
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                unique_entities.append(entity)

        for entity in unique_entities:
            masked_text = (
                masked_text[:entity.start] +
                entity.placeholder +
                masked_text[entity.end:]
            )
            mapping[entity.placeholder] = entity.original_value

        processing_time = time.time() - start_time

        # 감지된 엔티티 정리
        detected_entities: Dict[str, List[str]] = {}
        for entity in entities:
            if entity.entity_type not in detected_entities:
                detected_entities[entity.entity_type] = []
            if entity.original_value not in detected_entities[entity.entity_type]:
                detected_entities[entity.entity_type].append(entity.original_value)

        logger.info(
            f"PII Masking completed: mode={self.mode.value}, "
            f"entities={len(mapping)}, time={processing_time:.2f}s"
        )

        return masked_text, mapping

    def mask_with_result(self, text: str) -> MaskingResult:
        """
        텍스트 마스킹 (상세 결과 반환)

        Args:
            text: 마스킹할 텍스트

        Returns:
            MaskingResult 객체
        """
        start_time = time.time()
        masked_text, mapping = self.mask(text)
        processing_time = time.time() - start_time

        # 감지된 엔티티 타입별 분류
        detected_entities: Dict[str, List[str]] = {}
        for placeholder, value in mapping.items():
            # 플레이스홀더에서 타입 추출: [TYPE_N] -> TYPE
            match = re.match(r'\[(\w+)_\d+\]', placeholder)
            if match:
                entity_type = match.group(1)
                if entity_type not in detected_entities:
                    detected_entities[entity_type] = []
                detected_entities[entity_type].append(value)

        return MaskingResult(
            masked_text=masked_text,
            mapping=mapping,
            detected_entities=detected_entities,
            processing_time=processing_time,
            mode=self.mode.value,
        )

    def restore(self, masked_text: str, mapping: Dict[str, str]) -> str:
        """
        마스킹된 텍스트 복원

        Args:
            masked_text: 마스킹된 텍스트
            mapping: 복원용 매핑 {placeholder: original_value}

        Returns:
            복원된 텍스트
        """
        restored = masked_text
        for placeholder, original in mapping.items():
            restored = restored.replace(placeholder, original)
        return restored

    def _llm_detect_pii(self, text: str, existing_entities: List[PIIEntity]) -> List[PIIEntity]:
        """
        LLM을 사용하여 이름/주소 추가 감지

        Args:
            text: 원본 텍스트
            existing_entities: 이미 감지된 엔티티들

        Returns:
            추가로 감지된 PIIEntity 리스트
        """
        if not self.llm_client:
            return []

        # 이미 마스킹된 위치 표시
        masked_positions = set()
        for entity in existing_entities:
            masked_positions.update(range(entity.start, entity.end))

        prompt = f"""당신은 한국어 법률 문서의 개인정보 감지 전문가입니다.
다음 텍스트에서 **사람 이름**과 **구체적인 주소**만 찾아주세요.

## 찾아야 할 것
1. **사람 이름**: 한국식 이름 (2-4글자 한글, 예: 김철수, 박영희)
2. **구체적인 주소**: 실제 위치를 식별할 수 있는 주소 (예: 서울특별시 강남구 테헤란로 123)

## 찾지 말아야 할 것
- 직책/역할: 대표이사, 임대인, 임차인, 고소인, 피고소인, 근로자
- 일반 명사: 국민은행, 신한은행, 회사, 아파트
- 법률 용어: 계약서, 보증금, 임금
- 이미 패턴으로 감지된 것: 주민번호, 전화번호, 이메일, 계좌번호

## 텍스트
{text[:3000]}

## 출력 형식 (JSON)
반드시 아래 형식으로만 출력하세요:
{{"names": ["이름1", "이름2"], "addresses": ["주소1", "주소2"]}}

이름이나 주소가 없으면 빈 배열로 출력: {{"names": [], "addresses": []}}
"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "당신은 JSON만 출력하는 PII 감지 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            # JSON 파싱
            import json
            # JSON 블록 추출 (```json ... ``` 형식 처리)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content)

            new_entities = []

            # 이름 처리
            for name in result.get("names", []):
                if not name or len(name) < 2:
                    continue
                # 텍스트에서 위치 찾기
                for match in re.finditer(re.escape(name), text):
                    # 이미 감지된 위치가 아닌 경우만 추가
                    if not any(pos in masked_positions for pos in range(match.start(), match.end())):
                        placeholder = self._get_next_placeholder("PERSON_NAME")
                        new_entities.append(PIIEntity(
                            entity_type="PERSON_NAME",
                            original_value=name,
                            placeholder=placeholder,
                            start=match.start(),
                            end=match.end(),
                            score=0.8,
                        ))
                        # 동일한 이름이 여러 번 나오면 모두 마스킹
                        masked_positions.update(range(match.start(), match.end()))

            # 주소 처리
            for addr in result.get("addresses", []):
                if not addr or len(addr) < 5:
                    continue
                for match in re.finditer(re.escape(addr), text):
                    if not any(pos in masked_positions for pos in range(match.start(), match.end())):
                        placeholder = self._get_next_placeholder("ADDRESS")
                        new_entities.append(PIIEntity(
                            entity_type="ADDRESS",
                            original_value=addr,
                            placeholder=placeholder,
                            start=match.start(),
                            end=match.end(),
                            score=0.7,
                        ))
                        masked_positions.update(range(match.start(), match.end()))

            logger.info(f"LLM detected: {len(result.get('names', []))} names, {len(result.get('addresses', []))} addresses")
            return new_entities

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM PII detection error: {e}")
            return []


# ============================================================================
# 편의 함수
# ============================================================================

_default_masker: Optional[PIIMasker] = None


def get_masker(mode: str = "balanced") -> PIIMasker:
    """
    기본 PIIMasker 인스턴스 반환 (싱글톤)
    """
    global _default_masker
    if _default_masker is None or _default_masker.mode.value != mode:
        _default_masker = PIIMasker(mode=mode)
    return _default_masker


def mask_text(text: str, mode: str = "balanced") -> Tuple[str, Dict[str, str]]:
    """
    텍스트 마스킹 (편의 함수)

    Args:
        text: 마스킹할 텍스트
        mode: "fast" 또는 "balanced"

    Returns:
        (masked_text, mapping)
    """
    masker = get_masker(mode)
    return masker.mask(text)


def restore_text(masked_text: str, mapping: Dict[str, str]) -> str:
    """
    마스킹된 텍스트 복원 (편의 함수)

    Args:
        masked_text: 마스킹된 텍스트
        mapping: 복원용 매핑

    Returns:
        복원된 텍스트
    """
    masker = get_masker()
    return masker.restore(masked_text, mapping)


# ============================================================================
# LLM 호출 래퍼 (마스킹 자동 적용)
# ============================================================================

class MaskedLLMWrapper:
    """
    LLM 호출 시 자동으로 마스킹/복원을 적용하는 래퍼

    사용 예:
        wrapper = MaskedLLMWrapper(llm_client, mode="balanced")
        response = wrapper.generate("김철수(010-1234-5678)의 계약서를 요약해줘")
        # → 내부적으로 마스킹 후 LLM 호출, 응답 복원하여 반환
    """

    def __init__(
        self,
        llm_client: Any,
        model: str = "gpt-4o-mini",
        mode: str = "balanced",
    ):
        self.llm_client = llm_client
        self.model = model
        self.masker = PIIMasker(mode=mode)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        """
        마스킹된 프롬프트로 LLM 호출 후 응답 복원
        """
        # 1. 마스킹
        masked_prompt, mapping = self.masker.mask(prompt)

        # 시스템 프롬프트도 마스킹 (있는 경우)
        system_mapping = {}
        if system_prompt:
            masked_system, system_mapping = self.masker.mask(system_prompt)
        else:
            masked_system = None

        # 매핑 병합
        full_mapping = {**mapping, **system_mapping}

        # 2. LLM 호출
        messages = []
        if masked_system:
            messages.append({"role": "system", "content": masked_system})
        messages.append({"role": "user", "content": masked_prompt})

        response = self.llm_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        masked_response = response.choices[0].message.content

        # 3. 복원
        restored_response = self.masker.restore(masked_response, full_mapping)

        return restored_response

    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        """
        비동기 버전
        """
        # 동기 버전과 동일한 로직 (async 클라이언트 사용 시 수정 필요)
        return self.generate(prompt, system_prompt, temperature, max_tokens, **kwargs)


# ============================================================================
# Backward Compatibility Alias
# ============================================================================

class PiiMasker(PIIMasker):
    """
    Backward-compatible alias for PIIMasker.

    Supports old-style initialization with use_llm parameter.
    """

    def __init__(self, use_llm: bool = False, mode: str = None, **kwargs):
        # use_llm=True maps to "balanced" mode (uses local LLM for name/address)
        # use_llm=False maps to "fast" mode (Presidio only)
        if mode is None:
            mode = "balanced" if use_llm else "fast"
        super().__init__(mode=mode, **kwargs)

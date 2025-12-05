"""
사건 분석 서비스
업로드된 문서들을 AI로 분석하여 사건 정보 추출

Phase 1: 형사법 특화 분석 메서드 추가
- analyze_criminal_case: 형사 사건 분석
- _detect_crime_type: 범죄 유형 감지
- _analyze_crime_elements: 구성요건 분석
- _extract_sentencing_factors: 양형인자 추출
- _estimate_sentence: 양형 예측
- _suggest_defense_strategies: 변호 전략 제안
- _search_criminal_precedents: 형사 판례 검색
"""

from typing import List, Dict, Any, Optional
import logging
import json
import os

from apps.ai_service.models.criminal_analysis import (
    CriminalAnalysisResult,
    CrimeElements,
    CrimeElement,
    SentencingFactors,
    ExpectedSentence,
    CriminalPrecedent,
)
from apps.ai_service.models.criminal_case import (
    CriminalStage,
    CriminalCaseWithAnalysis,
    CriminalCaseResponse,
)
from datetime import datetime

logger = logging.getLogger(__name__)


# 한국 형법 주요 범죄 유형 목록
CRIME_TYPES = [
    "절도", "강도", "사기", "횡령", "배임",
    "폭행", "상해", "살인", "강간", "성추행",
    "마약", "음주운전", "교통사고",
    "명예훼손", "모욕", "협박",
    "뇌물", "직무유기", "위증",
]

# 형사 문서 유형 키워드
CRIMINAL_DOC_KEYWORDS = {
    "기소장": ["피고인", "공소사실", "적용법조", "공소제기"],
    "공소장": ["피고인", "공소사실", "적용법조"],
    "피의자신문조서": ["피의자", "진술", "조사", "경찰"],
    "고소장": ["고소인", "피고소인", "고소취지", "범죄사실"],
    "판결문": ["판결", "피고인", "선고", "형"],
    "수사보고서": ["수사", "보고", "증거"],
}


class CaseAnalyzer:
    """사건 분석 클래스"""

    def __init__(self, llm_client, retriever=None):
        """
        Args:
            llm_client: LLM 클라이언트 (OpenAI 등)
            retriever: RAG 검색기 (선택사항)
        """
        self.llm = llm_client
        self.retriever = retriever

    async def analyze_documents(
        self,
        texts: List[str],
        filenames: List[str]
    ) -> Dict[str, Any]:
        """
        문서 AI 분석

        Args:
            texts: 추출된 텍스트 리스트
            filenames: 파일명 리스트

        Returns:
            {
                "summary": "사건 요약",
                "document_types": ["판결문", "계약서"],
                "issues": ["쟁점1", "쟁점2"],
                "key_dates": {"선고일": "2024-01-15"},
                "parties": {"원고": "홍길동", "피고": "김철수"},
                "related_cases": [...],
                "suggested_case_name": "AI 제안 사건명"
            }
        """
        try:
            # 1. 전체 문서 결합
            combined_text = "\n\n=== 문서 구분 ===\n\n".join(
                [f"[{filename}]\n{text}" for filename, text in zip(filenames, texts)]
            )

            # 2. AI로 문서 분석
            analysis_prompt = f"""다음 법률 문서들을 분석하여 JSON 형식으로 정보를 추출해주세요.

문서:
{combined_text[:10000]}  # 토큰 제한으로 일부만

분석 항목:
1. summary: 사건 전체 요약 (3-5문장)
2. document_types: 문서 유형 리스트 (예: ["판결문", "계약서", "진단서"])
3. issues: 주요 법적 쟁점 리스트 (3-5개)
4. key_dates: 중요 날짜 딕셔너리 (예: {{"사고일": "2024-01-15", "제소일": "2024-03-01"}})
5. parties: 당사자 정보 (예: {{"원고": "홍길동", "피고": "김철수"}})
6. suggested_case_name: 사건명 제안 (예: "교통사고 2024-가합-12345")

JSON 형식으로만 응답하세요."""

            response = self.llm.generate(
                prompt=analysis_prompt,
                temperature=0.1,
                max_tokens=1500
            )

            # JSON 파싱 시도
            try:
                # 응답에서 JSON 부분만 추출
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    raise ValueError("JSON not found in response")
            except:
                # JSON 파싱 실패 시 기본 구조 생성
                logger.warning("Failed to parse JSON from LLM response, using fallback")
                analysis = {
                    "summary": response[:500],
                    "document_types": self._classify_documents(texts, filenames),
                    "issues": [],
                    "key_dates": {},
                    "parties": {},
                    "suggested_case_name": f"사건_{filenames[0][:20]}"
                }

            # 3. 관련 판례 검색 (RAG)
            if self.retriever and analysis.get("summary"):
                related_cases = await self._search_related_cases(analysis["summary"])
                analysis["related_cases"] = related_cases
            else:
                analysis["related_cases"] = []

            # 4. 다음 단계 제안
            analysis["suggested_next_steps"] = self._suggest_next_steps(analysis)

            logger.info(f"Successfully analyzed {len(texts)} documents")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze documents: {e}")
            # Fallback: 기본 분석 결과 반환
            return {
                "summary": f"{len(texts)}개의 문서가 업로드되었습니다. 수동으로 확인이 필요합니다.",
                "document_types": self._classify_documents(texts, filenames),
                "issues": [],
                "key_dates": {},
                "parties": {},
                "related_cases": [],
                "suggested_case_name": f"새 사건_{filenames[0][:20]}",
                "suggested_next_steps": ["문서 내용 검토", "법적 쟁점 파악"]
            }

    def _classify_documents(self, texts: List[str], filenames: List[str]) -> List[str]:
        """문서 유형 자동 분류 (간단한 휴리스틱)"""
        types = []
        for text, filename in zip(texts, filenames):
            text_lower = text.lower()
            filename_lower = filename.lower()

            if '판결' in text or '선고' in text or 'judgment' in filename_lower:
                types.append("판결문")
            elif '계약' in text or 'contract' in filename_lower:
                types.append("계약서")
            elif '진단' in text or '의무기록' in text:
                types.append("진단서/의무기록")
            elif '증명' in text:
                types.append("증명서")
            else:
                types.append("기타 문서")

        return list(set(types))  # 중복 제거

    async def _search_related_cases(self, query: str) -> List[Dict[str, Any]]:
        """
        RAG로 관련 판례 검색

        VectorDB 메타데이터 구조:
        - case_number: 사건번호 (예: "2023노7795")
        - court: 법원명 (예: "수원지방법원")
        - decision_date: 선고일 (예: "2023.11.15")
        - source: 원본 파일명 (예: "HS_P_314016")
        - type: 문서 타입 (예: "precedent")
        """
        try:
            # 메타데이터 필터: 판례만 검색
            filter_metadata = {"type": "precedent"}

            results = self.retriever.retrieve(
                query=query,
                top_k=5,
                filter_metadata=filter_metadata
            )

            related_cases = []
            for idx, result in enumerate(results, 1):
                metadata = result.get('metadata', {})

                # Title 생성 (우선순위: case_number > court > source > fallback)
                case_number = metadata.get('case_number', '')
                court = metadata.get('court', '')
                source = metadata.get('source', '')

                if case_number and court:
                    title = f"{court} {case_number}"
                elif case_number:
                    title = f"판례 {case_number}"
                elif court:
                    title = f"{court} 판결"
                elif source:
                    title = f"판례 ({source})"
                else:
                    title = f"관련 판례 {idx}"

                # Summary: 더 긴 텍스트 활용 (200자 → 350자)
                summary_text = result.get('text', '').strip()
                summary = summary_text[:350] + "..." if len(summary_text) > 350 else summary_text

                # Date 정리
                date = metadata.get('decision_date', metadata.get('date', ''))

                related_cases.append({
                    "title": title,
                    "summary": summary,
                    "date": date,
                    "relevance": round(result.get('score', 0) * 100, 1),
                    "case_number": case_number,
                    "court": court
                })

            logger.info(f"Found {len(related_cases)} related precedents for query: '{query[:50]}...'")
            return related_cases

        except Exception as e:
            logger.error(f"Failed to search related cases: {e}", exc_info=True)
            return []

    def _suggest_next_steps(self, analysis: Dict[str, Any]) -> List[str]:
        """다음 단계 제안"""
        steps = []

        # 쟁점이 있으면 추가 조사 제안
        if analysis.get("issues"):
            steps.append("주요 쟁점별 판례 조사")

        # 당사자 정보가 있으면 증거 수집 제안
        if analysis.get("parties"):
            steps.append("증거 자료 보강")

        # 관련 판례가 있으면 분석 제안
        if analysis.get("related_cases"):
            steps.append("관련 판례 상세 분석")

        # 기본 제안
        if not steps:
            steps = [
                "법률 검토 및 전략 수립",
                "추가 증거 자료 수집",
                "상대방 주장 예상 및 대응"
            ]

        return steps

    # =========================================================================
    # 형사법 특화 분석 메서드 (Phase 1)
    # =========================================================================

    async def analyze_criminal_case(
        self,
        texts: List[str],
        filenames: List[str],
        crime_type: Optional[str] = None,
    ) -> CriminalAnalysisResult:
        """
        형사 사건 분석 (Phase 1 핵심 메서드)

        Args:
            texts: 추출된 텍스트 리스트
            filenames: 파일명 리스트
            crime_type: 범죄 유형 (선택, 자동 감지 가능)

        Returns:
            CriminalAnalysisResult
        """
        try:
            logger.info(f"Starting criminal case analysis for {len(texts)} documents")

            # 1. 문서 결합
            combined_text = "\n\n=== 문서 구분 ===\n\n".join(
                [f"[{fname}]\n{text[:5000]}" for fname, text in zip(filenames, texts)]
            )

            # 2. 기존 분석 호출 (요약, 쟁점 등)
            base_analysis = await self.analyze_documents(texts, filenames)
            summary = base_analysis.get("summary", "")

            # 3. 범죄 유형 감지
            if not crime_type:
                crime_type = await self._detect_crime_type(combined_text)
            logger.info(f"Detected crime type: {crime_type}")

            # 4. 구성요건 분석
            crime_elements = await self._analyze_crime_elements(combined_text, crime_type)

            # 5. 양형인자 추출
            sentencing_factors = await self._extract_sentencing_factors(combined_text, crime_type)

            # 6. 양형 예측
            expected_sentence = await self._estimate_sentence(crime_type, sentencing_factors)

            # 7. 변호 전략 제안
            defense_strategies = await self._suggest_defense_strategies(crime_type, crime_elements, sentencing_factors)

            # 8. 형사 판례 검색
            related_precedents = await self._search_criminal_precedents(crime_type, crime_elements)

            result = CriminalAnalysisResult(
                summary=summary,
                crime_type=crime_type,
                crime_elements=crime_elements,
                sentencing_factors=sentencing_factors,
                expected_sentence=expected_sentence,
                defense_strategies=defense_strategies,
                related_precedents=related_precedents,
            )

            logger.info(f"Criminal case analysis completed: {crime_type}")
            return result

        except Exception as e:
            logger.error(f"Criminal case analysis failed: {e}", exc_info=True)
            # Fallback: 기본 결과 반환
            return CriminalAnalysisResult(
                summary=f"분석 중 오류 발생: {str(e)}",
                crime_type=crime_type or "미상",
                crime_elements=CrimeElements(objective=[], subjective=[]),
                sentencing_factors=SentencingFactors(favorable=[], unfavorable=[]),
                expected_sentence=ExpectedSentence(
                    range="판단 불가",
                    suspended_probability=0.0,
                    reasoning="분석 실패",
                ),
                defense_strategies=["전문 변호사 상담 권장"],
                related_precedents=[],
            )

    async def _detect_crime_type(self, text: str) -> str:
        """
        범죄 유형 자동 감지

        Args:
            text: 문서 텍스트

        Returns:
            범죄 유형 문자열
        """
        try:
            # 먼저 휴리스틱으로 빠르게 감지 시도
            text_lower = text.lower()
            for crime in CRIME_TYPES:
                if crime in text_lower:
                    return crime

            # LLM으로 감지
            prompt = f"""다음 법률 문서에서 범죄 유형을 식별하세요.

문서 (첫 3000자):
{text[:3000]}

가능한 범죄 유형:
{', '.join(CRIME_TYPES)}

위 목록에서 가장 적합한 범죄 유형 하나만 응답하세요.
다른 설명 없이 범죄 유형만 출력하세요.
"""
            response = self.llm.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=50,
            )

            # 응답에서 범죄 유형 추출
            response_clean = response.strip()
            for crime in CRIME_TYPES:
                if crime in response_clean:
                    return crime

            return response_clean[:20]  # fallback

        except Exception as e:
            logger.warning(f"Crime type detection failed: {e}")
            return "미상"

    async def _analyze_crime_elements(
        self,
        text: str,
        crime_type: str,
    ) -> CrimeElements:
        """
        구성요건 분석

        Args:
            text: 문서 텍스트
            crime_type: 범죄 유형

        Returns:
            CrimeElements
        """
        try:
            prompt = f"""다음 {crime_type} 사건에서 구성요건을 분석하세요.

문서:
{text[:5000]}

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

            response = self.llm.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=1000,
            )

            # JSON 파싱
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                data = json.loads(response[json_start:json_end])

                objective = [
                    CrimeElement(
                        element=e.get("element", ""),
                        description=e.get("description", ""),
                        fulfilled=e.get("fulfilled", False),
                    )
                    for e in data.get("objective", [])
                ]
                subjective = [
                    CrimeElement(
                        element=e.get("element", ""),
                        description=e.get("description", ""),
                        fulfilled=e.get("fulfilled", False),
                    )
                    for e in data.get("subjective", [])
                ]

                return CrimeElements(objective=objective, subjective=subjective)

        except Exception as e:
            logger.warning(f"Crime elements analysis failed: {e}")

        # Fallback
        return CrimeElements(
            objective=[
                CrimeElement(element="분석 필요", description="상세 분석이 필요합니다", fulfilled=False)
            ],
            subjective=[
                CrimeElement(element="분석 필요", description="상세 분석이 필요합니다", fulfilled=False)
            ],
        )

    async def _extract_sentencing_factors(
        self,
        text: str,
        crime_type: str,
    ) -> SentencingFactors:
        """
        양형인자 추출

        Args:
            text: 문서 텍스트
            crime_type: 범죄 유형

        Returns:
            SentencingFactors
        """
        try:
            prompt = f"""다음 {crime_type} 사건에서 양형인자를 추출하세요.

문서:
{text[:5000]}

양형인자 분류:
- 유리한 정상: 초범, 반성, 피해회복, 합의, 자수, 우발적 범행, 고령, 건강문제 등
- 불리한 정상: 동종전과, 계획적 범행, 피해 중대, 범행 후 태도 불량, 피해자 다수 등

JSON 형식으로만 응답하세요:
{{
    "favorable": ["인자1", "인자2"],
    "unfavorable": ["인자1", "인자2"]
}}"""

            response = self.llm.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=500,
            )

            # JSON 파싱
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                return SentencingFactors(
                    favorable=data.get("favorable", []),
                    unfavorable=data.get("unfavorable", []),
                )

        except Exception as e:
            logger.warning(f"Sentencing factors extraction failed: {e}")

        return SentencingFactors(favorable=[], unfavorable=[])

    async def _estimate_sentence(
        self,
        crime_type: str,
        factors: SentencingFactors,
    ) -> ExpectedSentence:
        """
        양형 예측

        Args:
            crime_type: 범죄 유형
            factors: 양형인자

        Returns:
            ExpectedSentence
        """
        try:
            prompt = f"""다음 조건에서 예상 양형을 산정하세요.

범죄 유형: {crime_type}
유리한 정상: {', '.join(factors.favorable) if factors.favorable else '없음'}
불리한 정상: {', '.join(factors.unfavorable) if factors.unfavorable else '없음'}

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

            response = self.llm.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=500,
            )

            # JSON 파싱
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                data = json.loads(response[json_start:json_end])

                prob = data.get("suspended_probability", 0.5)
                if isinstance(prob, str):
                    prob = float(prob.replace("%", "")) / 100 if "%" in prob else float(prob)
                prob = max(0.0, min(1.0, prob))

                return ExpectedSentence(
                    range=data.get("range", "판단 필요"),
                    suspended_probability=prob,
                    reasoning=data.get("reasoning"),
                )

        except Exception as e:
            logger.warning(f"Sentence estimation failed: {e}")

        # Fallback: 일반적인 양형 범위
        return ExpectedSentence(
            range="개별 사안에 따라 다름",
            suspended_probability=0.5,
            reasoning="상세 분석 필요",
        )

    async def _suggest_defense_strategies(
        self,
        crime_type: str,
        elements: CrimeElements,
        factors: SentencingFactors,
    ) -> List[str]:
        """
        변호 전략 제안

        Args:
            crime_type: 범죄 유형
            elements: 구성요건 분석 결과
            factors: 양형인자

        Returns:
            변호 전략 리스트
        """
        strategies = []

        # 1. 구성요건 미충족 시 무죄/혐의없음 주장
        all_elements = elements.objective + elements.subjective
        unfulfilled = [e for e in all_elements if not e.fulfilled]
        if unfulfilled:
            elements_str = ", ".join([e.element for e in unfulfilled])
            strategies.append(f"구성요건 미충족 주장 ({elements_str})")

        # 2. 유리한 양형인자 강조
        if factors.favorable:
            strategies.append(f"유리한 정상 강조 ({', '.join(factors.favorable[:3])})")

        # 3. 피해회복 권장
        if "피해회복" not in factors.favorable and "합의" not in factors.favorable:
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
        elif crime_type in ["음주운전"]:
            strategies.append("알코올 치료 프로그램 이수")

        return strategies[:6]  # 최대 6개

    async def _search_criminal_precedents(
        self,
        crime_type: str,
        elements: CrimeElements,
    ) -> List[CriminalPrecedent]:
        """
        형사 판례 검색 (양형 통계 포함)

        Args:
            crime_type: 범죄 유형
            elements: 구성요건 분석

        Returns:
            CriminalPrecedent 리스트
        """
        if not self.retriever:
            return []

        try:
            # 검색 쿼리 생성
            element_keywords = " ".join([e.element for e in elements.objective[:3]])
            query = f"{crime_type} {element_keywords} 판례"

            # 메타데이터 필터
            filter_metadata = {
                "type": "precedent",
            }

            results = self.retriever.retrieve(
                query=query,
                top_k=10,
                filter_metadata=filter_metadata,
            )

            precedents = []
            for result in results:
                metadata = result.get("metadata", {})

                # 형량 정보 추출
                text = result.get("text", "")
                sentence = self._extract_sentence_from_text(text)

                precedent = CriminalPrecedent(
                    case_number=metadata.get("case_number", ""),
                    court=metadata.get("court", ""),
                    date=metadata.get("decision_date", ""),
                    crime_type=crime_type,
                    sentence=sentence,
                    summary=text[:350],
                    relevance=round(result.get("score", 0) * 100, 1),
                )
                precedents.append(precedent)

            logger.info(f"Found {len(precedents)} criminal precedents for {crime_type}")
            return precedents

        except Exception as e:
            logger.error(f"Criminal precedent search failed: {e}")
            return []

    def _extract_sentence_from_text(self, text: str) -> str:
        """
        판결문 텍스트에서 형량 정보 추출

        Args:
            text: 판결문 텍스트

        Returns:
            형량 문자열
        """
        import re

        # 형량 패턴들
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

    def _classify_criminal_documents(
        self,
        texts: List[str],
        filenames: List[str],
    ) -> List[str]:
        """
        형사 문서 유형 분류

        Args:
            texts: 문서 텍스트 리스트
            filenames: 파일명 리스트

        Returns:
            문서 유형 리스트
        """
        types = []

        for text, filename in zip(texts, filenames):
            text_sample = text[:2000].lower()

            for doc_type, keywords in CRIMINAL_DOC_KEYWORDS.items():
                if any(kw in text_sample for kw in keywords):
                    types.append(doc_type)
                    break
            else:
                # 기존 분류 사용
                types.extend(self._classify_documents([text], [filename]))

        return list(set(types))

    # =========================================================================
    # 형사 사건 분석 + DB 저장 (Phase 1)
    # =========================================================================

    async def analyze_and_save_criminal_case(
        self,
        texts: List[str],
        filenames: List[str],
        user_id: str,
        case_name: Optional[str] = None,
        crime_type: Optional[str] = None,
        db_session=None,
    ) -> CriminalCaseResponse:
        """
        형사 사건 분석 및 DB 저장

        1. 문서 분석 수행
        2. 분석 결과를 DB에 저장
        3. 저장된 사건 반환

        Args:
            texts: 추출된 텍스트 리스트
            filenames: 파일명 리스트
            user_id: 사용자 ID
            case_name: 사건명 (선택, 미지정시 자동 생성)
            crime_type: 범죄 유형 (선택, 미지정시 자동 감지)
            db_session: 데이터베이스 세션 (선택)

        Returns:
            CriminalCaseResponse: 저장된 사건 정보
        """
        try:
            logger.info(f"[analyze_and_save_criminal_case] Starting for user={user_id}, files={len(filenames)}")

            # 1. 분석 수행
            analysis = await self.analyze_criminal_case(texts, filenames, crime_type)

            # 2. 사건명 생성 (제공되지 않은 경우)
            if not case_name:
                # 파일 이름이 있으면 파일 이름 사용 (확장자 제거)
                if filenames and filenames[0]:
                    # 확장자 제거
                    base_name = os.path.splitext(filenames[0])[0]
                    # 여러 파일인 경우 "파일명 외 N건"
                    if len(filenames) > 1:
                        case_name = f"{base_name} 외 {len(filenames) - 1}건"
                    else:
                        case_name = base_name
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    case_name = f"{analysis.crime_type} 사건 ({date_str})"

            # 3. 양형인자에서 조건 태그 추출
            conditions = self._extract_conditions(analysis.sentencing_factors)

            # 4. 업로드 파일 정보 구성
            uploaded_files = [
                {"filename": f, "uploaded_at": datetime.now().isoformat()}
                for f in filenames
            ]

            # 5. CriminalCaseWithAnalysis 데이터 구성
            case_data = CriminalCaseWithAnalysis(
                case_name=case_name,
                summary=analysis.summary,
                crime_type=analysis.crime_type,
                stage=CriminalStage.COMPLAINT,  # 초기 단계
                conditions=conditions,
                schedules=[],  # 초기에는 일정 없음
                crime_elements=analysis.crime_elements.model_dump(),
                sentencing_factors=analysis.sentencing_factors.model_dump(),
                expected_sentence=analysis.expected_sentence.model_dump(),
                defense_strategies=analysis.defense_strategies,
                related_precedents=[p.model_dump() for p in analysis.related_precedents],
                uploaded_files=uploaded_files,
            )

            # 6. DB 저장
            if db_session:
                from apps.ai_service.services.criminal_case_service import CriminalCaseService
                case_service = CriminalCaseService(db_session)
                saved_case = await case_service.create_case_with_analysis(user_id, case_data)
                logger.info(f"[analyze_and_save_criminal_case] Saved case: {saved_case.id}")
                return saved_case
            else:
                # DB 세션 없을 경우 분석 결과만 반환 (저장 없음)
                logger.warning("[analyze_and_save_criminal_case] No DB session provided, skipping save")
                return CriminalCaseResponse(
                    id="temp-" + datetime.now().strftime("%Y%m%d%H%M%S"),
                    user_id=user_id,
                    case_name=case_name,
                    summary=analysis.summary,
                    crime_type=analysis.crime_type,
                    crime_elements=analysis.crime_elements.model_dump(),
                    sentencing_factors=analysis.sentencing_factors.model_dump(),
                    expected_sentence=analysis.expected_sentence.model_dump(),
                    defense_strategies=analysis.defense_strategies,
                    related_precedents=[p.model_dump() for p in analysis.related_precedents],
                    stage=CriminalStage.COMPLAINT,
                    schedules=[],
                    conditions=conditions,
                    uploaded_files=uploaded_files,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )

        except Exception as e:
            logger.error(f"[analyze_and_save_criminal_case] Failed: {e}", exc_info=True)
            raise

    def _extract_conditions(self, factors: SentencingFactors) -> List[str]:
        """
        양형인자에서 조건 태그 추출 (유사 사건 검색용)

        Args:
            factors: 양형인자

        Returns:
            조건 태그 리스트
        """
        conditions = []

        # 유리한 정상에서 조건 추출
        favorable_keywords = {
            "초범": "초범",
            "반성": "반성",
            "피해회복": "피해회복",
            "피해 회복": "피해회복",
            "합의": "합의",
            "자수": "자수",
            "자백": "자백",
            "우발": "우발적 범행",
            "고령": "고령",
            "질병": "건강문제",
            "건강": "건강문제",
        }
        for factor in factors.favorable:
            factor_lower = factor.lower()
            for keyword, tag in favorable_keywords.items():
                if keyword in factor_lower:
                    conditions.append(tag)

        # 불리한 정상에서 조건 추출
        unfavorable_keywords = {
            "전과": "전과",
            "동종전과": "동종전과",
            "동종 전과": "동종전과",
            "이종전과": "이종전과",
            "이종 전과": "이종전과",
            "계획적": "계획적 범행",
            "계획범행": "계획적 범행",
            "조직": "조직적 범행",
            "상습": "상습범",
            "피해 중대": "중대 피해",
            "중대 피해": "중대 피해",
            "반성 없": "반성 없음",
        }
        for factor in factors.unfavorable:
            factor_lower = factor.lower()
            for keyword, tag in unfavorable_keywords.items():
                if keyword in factor_lower:
                    conditions.append(tag)

        return list(set(conditions))

"""
사건 분석 서비스
업로드된 문서들을 AI로 분석하여 사건 정보 추출
"""

from typing import List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


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
        """RAG로 관련 판례 검색"""
        try:
            results = self.retriever.retrieve(
                query=query,
                top_k=5
            )

            related_cases = []
            for result in results:
                metadata = result.get('metadata', {})
                related_cases.append({
                    "title": metadata.get('title', 'Unknown'),
                    "summary": result.get('text', '')[:200],
                    "date": metadata.get('date', ''),
                    "relevance": round(result.get('score', 0) * 100, 1)
                })

            return related_cases

        except Exception as e:
            logger.error(f"Failed to search related cases: {e}")
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

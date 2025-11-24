"""
Key Clause Extraction Service
핵심 조항 추출 서비스
"""

from typing import Dict, Any, List, Optional
import json
import re
import logging

logger = logging.getLogger(__name__)


class ClauseExtractor:
    """
    Key Clause Extractor using LLM

    Extracts important clauses from legal documents such as:
    - Contract terms
    - Obligations
    - Payment terms
    - Termination conditions
    - Liability clauses
    """

    # Clause type mapping
    CLAUSE_TYPES = {
        "PAYMENT": "지급조건",
        "OBLIGATION": "의무사항",
        "TERMINATION": "해지조건",
        "LIABILITY": "책임조항",
        "WARRANTY": "보증조항",
        "CONFIDENTIALITY": "비밀유지",
        "IP": "지적재산권",
        "DISPUTE": "분쟁해결",
        "GENERAL": "일반조항",
        "OTHER": "기타"
    }

    def __init__(self, llm_client):
        """
        Initialize ClauseExtractor with LLM client

        Args:
            llm_client: LLM client instance (from libs.rag_core)
        """
        self.llm = llm_client

    async def extract_clauses(
        self,
        text: str,
        document_id: Optional[str] = None,
        doc_type: Optional[str] = None,
        llm_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract key clauses from document using LLM

        Args:
            text: Document text to analyze
            document_id: Optional document ID for reference
            doc_type: Document type (CONTRACT, STATUTE, etc.)
            llm_model: LLM model name (for metadata only)

        Returns:
            {
                "clauses": [
                    {
                        "clause_type": "PAYMENT",
                        "title": "지급 조건",
                        "content": "조항 내용...",
                        "importance_score": 85
                    },
                    ...
                ],
                "total_count": 5
            }
        """
        try:
            # Validate input
            if not text or len(text.strip()) == 0:
                raise ValueError("Text cannot be empty")

            # Prepare prompt
            prompt = self._create_extraction_prompt(text, doc_type)

            # Call LLM
            logger.info(f"Extracting clauses for document {document_id} (type: {doc_type})...")

            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.2,  # Very low temperature for consistent extraction
                max_tokens=2000
            )

            llm_output = response.get('text', '').strip()

            if not llm_output:
                raise ValueError("LLM returned empty response")

            # Parse LLM response to extract clauses
            clauses = self._parse_clauses(llm_output)

            logger.info(
                f"Extracted {len(clauses)} clauses for document {document_id}"
            )

            return {
                "clauses": clauses,
                "total_count": len(clauses)
            }

        except Exception as e:
            logger.error(f"Error extracting clauses: {e}", exc_info=True)
            raise

    def _create_extraction_prompt(self, text: str, doc_type: Optional[str]) -> str:
        """
        Create prompt for clause extraction

        Args:
            text: Document text
            doc_type: Document type

        Returns:
            Formatted prompt string
        """
        doc_type_hint = ""
        if doc_type == "CONTRACT":
            doc_type_hint = "이 문서는 계약서입니다. 계약 조건, 의무사항, 지급조건, 해지조건 등에 집중해주세요."
        elif doc_type == "STATUTE":
            doc_type_hint = "이 문서는 법령입니다. 주요 규정, 의무사항, 제재조항 등에 집중해주세요."
        elif doc_type == "PRECEDENT":
            doc_type_hint = "이 문서는 판례입니다. 판시사항, 판결이유, 법리적 쟁점 등에 집중해주세요."

        prompt = f"""당신은 전문 법률 문서 분석가입니다. 다음 문서에서 핵심 조항들을 추출해주세요.

{doc_type_hint}

문서 내용:
{text}

다음 형식의 JSON 배열로 핵심 조항들을 추출해주세요:

[
  {{
    "clause_type": "PAYMENT | OBLIGATION | TERMINATION | LIABILITY | WARRANTY | CONFIDENTIALITY | IP | DISPUTE | GENERAL | OTHER",
    "title": "조항 제목 (간단명료하게)",
    "content": "조항의 핵심 내용 (1-3문장으로 요약)",
    "importance_score": 0-100 사이의 점수 (중요도)
  }},
  ...
]

중요도 점수 기준:
- 90-100: 매우 중요 (계약의 핵심 조건, 법적 의무, 손해배상 등)
- 70-89: 중요 (주요 권리/의무, 지급조건, 해지조건 등)
- 50-69: 보통 (일반적 조항, 부가적 의무 등)
- 30-49: 낮음 (형식적 조항, 통상적 규정 등)

최소 3개, 최대 10개의 핵심 조항을 추출해주세요.
반드시 유효한 JSON 형식으로만 응답해주세요. 다른 설명은 포함하지 마세요."""

        return prompt

    def _parse_clauses(self, llm_output: str) -> List[Dict[str, Any]]:
        """
        Parse LLM output to extract clause list

        Args:
            llm_output: Raw LLM response text

        Returns:
            List of clause dictionaries
        """
        try:
            # Try to find JSON array in the output
            # Look for [...] pattern
            json_match = re.search(r'\[\s*\{.*?\}\s*\]', llm_output, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)
                clauses_raw = json.loads(json_str)
            else:
                # Try parsing the entire output as JSON
                clauses_raw = json.loads(llm_output)

            # Validate and normalize clauses
            clauses = []
            for clause_data in clauses_raw:
                clause = self._validate_clause(clause_data)
                if clause:
                    clauses.append(clause)

            return clauses

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}")
            logger.debug(f"LLM output was: {llm_output[:500]}...")

            # Fallback: try to extract clauses manually
            return self._manual_parse_clauses(llm_output)

    def _validate_clause(self, clause_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and normalize a clause object

        Args:
            clause_data: Raw clause data from LLM

        Returns:
            Validated clause dict or None if invalid
        """
        try:
            # Required fields
            clause_type = clause_data.get('clause_type', 'OTHER').upper()
            title = clause_data.get('title', '').strip()
            content = clause_data.get('content', '').strip()

            if not title or not content:
                logger.warning(f"Skipping clause with missing title or content: {clause_data}")
                return None

            # Normalize clause_type
            if clause_type not in self.CLAUSE_TYPES:
                clause_type = 'OTHER'

            # Importance score (default to 50 if not provided or invalid)
            try:
                importance_score = int(clause_data.get('importance_score', 50))
                importance_score = max(0, min(100, importance_score))  # Clamp to 0-100
            except (ValueError, TypeError):
                importance_score = 50

            return {
                "clause_type": clause_type,
                "title": title[:255],  # Limit title length
                "content": content,
                "importance_score": importance_score
            }

        except Exception as e:
            logger.warning(f"Error validating clause: {e}")
            return None

    def _manual_parse_clauses(self, llm_output: str) -> List[Dict[str, Any]]:
        """
        Fallback manual parsing when JSON parsing fails

        Args:
            llm_output: Raw LLM response

        Returns:
            List of clauses (may be empty if parsing fails completely)
        """
        logger.warning("Using fallback manual parsing for clauses")

        clauses = []

        # Try to identify clause-like patterns
        # Look for numbered lists or clear section markers
        lines = llm_output.split('\n')

        current_clause = None

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Look for title-like patterns (e.g., "1. 제목:", "제목:", "- 제목")
            title_match = re.match(r'^[\d\-\*]+[\.\):\s]*(.*?)[:\s]*$', line)

            if title_match and len(line) < 100:  # Likely a title
                # Save previous clause if exists
                if current_clause and current_clause.get('content'):
                    clauses.append(self._validate_clause(current_clause))

                # Start new clause
                current_clause = {
                    'title': title_match.group(1).strip(),
                    'content': '',
                    'clause_type': 'OTHER',
                    'importance_score': 50
                }
            elif current_clause:
                # Accumulate content
                if current_clause['content']:
                    current_clause['content'] += ' '
                current_clause['content'] += line

        # Add last clause
        if current_clause and current_clause.get('content'):
            clauses.append(self._validate_clause(current_clause))

        # Filter out None values
        clauses = [c for c in clauses if c is not None]

        if not clauses:
            # Last resort: create a single generic clause
            logger.error("Complete parsing failure, creating generic clause")
            clauses = [{
                'clause_type': 'OTHER',
                'title': '문서 내용',
                'content': llm_output[:500] + '...' if len(llm_output) > 500 else llm_output,
                'importance_score': 50
            }]

        return clauses

"""
Document Summarization Service
문서 요약 생성 서비스
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Summarizer:
    """
    Document Summarizer using LLM

    Generates concise summaries of legal documents including:
    - Contracts
    - Statutes
    - Cases
    - Precedents
    """

    def __init__(self, llm_client):
        """
        Initialize Summarizer with LLM client

        Args:
            llm_client: LLM client instance (from libs.rag_core)
        """
        self.llm = llm_client

    async def summarize(
        self,
        text: str,
        document_id: Optional[str] = None,
        summary_type: str = "GLOBAL",
        llm_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate document summary using LLM

        Args:
            text: Document text to summarize
            document_id: Optional document ID for reference
            summary_type: Type of summary (GLOBAL, SECTION, etc.)
            llm_model: LLM model name (for metadata only)

        Returns:
            {
                "summary": "요약 텍스트",
                "token_count": 1234,
                "model_version": "gpt-4-turbo-preview"
            }
        """
        try:
            # Validate input
            if not text or len(text.strip()) == 0:
                raise ValueError("Text cannot be empty")

            # Prepare prompt based on summary type
            prompt = self._create_summary_prompt(text, summary_type)

            # Call LLM (synchronous method returns string directly)
            logger.info(f"Generating {summary_type} summary for document {document_id}...")

            response = self.llm.generate(
                prompt=prompt,
                temperature=0.3,  # Low temperature for consistent summaries
                max_tokens=1000
            )

            # response is a string, not a dict
            summary_text = response.strip() if response else ""

            if not summary_text:
                raise ValueError("LLM returned empty summary")

            # Prepare result
            result = {
                "summary": summary_text,
                "token_count": self._estimate_token_count(summary_text),
                "model_version": llm_model or "unknown"
            }

            logger.info(
                f"Summary generated successfully for document {document_id}: "
                f"{len(summary_text)} chars, ~{result['token_count']} tokens"
            )

            return result

        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            raise

    def _create_summary_prompt(self, text: str, summary_type: str) -> str:
        """
        Create appropriate prompt based on summary type

        Args:
            text: Document text
            summary_type: GLOBAL, SECTION, etc.

        Returns:
            Formatted prompt string
        """
        if summary_type == "GLOBAL":
            prompt = f"""당신은 전문 법률 문서 분석가입니다. 다음 문서를 간결하고 명확하게 요약해주세요.

문서 내용:
{text}

다음 사항을 포함하여 요약해주세요:
1. 문서의 주요 목적 및 핵심 내용
2. 주요 당사자 (해당시)
3. 중요한 조건, 의무사항, 또는 권리 (해당시)
4. 주목할만한 특이사항이나 리스크 (해당시)

요약은 3-5개 문단으로, 핵심만 간결하게 작성해주세요. 법률 전문용어는 필요시 사용하되, 명확하게 설명해주세요."""

        elif summary_type == "SECTION":
            prompt = f"""당신은 전문 법률 문서 분석가입니다. 다음 문서 섹션을 간결하게 요약해주세요.

섹션 내용:
{text}

이 섹션의 핵심 내용과 중요 포인트를 1-2개 문단으로 요약해주세요."""

        else:
            # Default to GLOBAL
            prompt = f"""당신은 전문 법률 문서 분석가입니다. 다음 문서의 핵심 내용을 간결하게 요약해주세요.

문서 내용:
{text}

핵심 내용을 3-5개 문단으로 요약해주세요."""

        return prompt

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

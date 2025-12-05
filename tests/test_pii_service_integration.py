import pytest
import os
from apps.ai_service.services.document_processor import DocumentProcessor
from apps.ai_service.services.pii_masker import PiiMasker

# Sample text with PII
SAMPLE_TEXT = """
임대차계약서
임대인: 김철수 (주민등록번호: 760815-1234567)
주소: 서울특별시 강남구 테헤란로 123, 456호
연락처: 010-1234-5678
이메일: kim.cs@example.com
계좌번호: 국민은행 123-45-678901
"""

@pytest.fixture
def document_processor():
    return DocumentProcessor(enable_masking=True)

def test_pii_masker_initialization():
    """Test that PiiMasker initializes correctly"""
    masker = PiiMasker(use_llm=False)
    assert masker.analyzer is not None
    assert masker.anonymizer is not None

def test_pii_masking_basic():
    """Test basic masking functionality (Presidio only)"""
    masker = PiiMasker(use_llm=False)
    result = masker.mask_document(SAMPLE_TEXT)
    
    print(f"Masked Text: {result.masked_text}")
    
    # Check if PII is masked
    assert "760815-1234567" not in result.masked_text
    assert "010-1234-5678" not in result.masked_text
    assert "kim.cs@example.com" not in result.masked_text
    assert "123-45-678901" not in result.masked_text
    
    # Check detected entities
    assert "KR_RRN" in result.detected_entities
    assert "KR_PHONE" in result.detected_entities
    assert "EMAIL_ADDRESS" in result.detected_entities

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key required")
def test_pii_masking_hybrid():
    """Test hybrid masking with LLM"""
    masker = PiiMasker(use_llm=True)
    result = masker.mask_document(SAMPLE_TEXT)
    
    print(f"Hybrid Masked Text: {result.masked_text}")
    
    # Check if Name and Address are masked (LLM features)
    # Note: This depends on LLM performance, so we check for presence of mask tags
    assert "[이름" in result.masked_text or "김철수" not in result.masked_text
    assert "[주소" in result.masked_text or "테헤란로" not in result.masked_text

def test_document_processor_integration(tmp_path):
    """Test integration with DocumentProcessor"""
    # Create a dummy file
    d = tmp_path / "test_doc.txt"
    d.write_text(SAMPLE_TEXT, encoding="utf-8")
    
    processor = DocumentProcessor(enable_masking=True)
    result = processor.process_document(str(d))
    
    assert result['success'] is True
    processed_text = result['text']
    
    # Verify text is masked
    assert "760815-1234567" not in processed_text
    
    # Verify metadata
    metadata = result['metadata']
    assert 'pii_detected' in metadata
    assert 'pii_masking_method' in metadata

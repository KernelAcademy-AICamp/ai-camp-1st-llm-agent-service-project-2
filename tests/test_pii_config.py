import pytest
import os
from unittest.mock import patch, MagicMock
from apps.ai_service.services.pii_masker import PiiMasker

def test_local_llm_configuration():
    """Test that PiiMasker correctly configures for Local LLM"""
    with patch.dict(os.environ, {
        "LLM_BASE_URL": "http://test-local:11434/v1",
        "LLM_API_KEY": "test-key",
        "LLM_MODEL": "test-model"
    }):
        # Mock OpenAI to avoid actual connection
        with patch("apps.ai_service.services.pii_masker.OpenAI") as MockOpenAI:
            masker = PiiMasker(use_llm=True)
            
            # Verify OpenAI client init
            MockOpenAI.assert_called_with(
                base_url="http://test-local:11434/v1",
                api_key="test-key"
            )
            assert masker.llm_model == "test-model"

def test_openai_fallback_configuration():
    """Test that PiiMasker falls back to OpenAI if Local LLM not set"""
    # Ensure no local LLM env vars
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
        with patch("apps.ai_service.services.pii_masker.OpenAI") as MockOpenAI:
            masker = PiiMasker(use_llm=True)
            
            # Verify OpenAI client init
            MockOpenAI.assert_called_with(api_key="sk-test")
            assert masker.llm_model == "gpt-4o-mini"

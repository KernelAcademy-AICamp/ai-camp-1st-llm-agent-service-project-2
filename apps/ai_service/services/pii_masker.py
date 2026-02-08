import os
import re
import logging
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Presidio
try:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

# OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class MaskingResult:
    """Masking result data class"""
    masked_text: str
    detected_entities: Dict[str, List[str]]
    processing_time: float
    method: str

class PiiMasker:
    """
    PII Masking Service using Presidio (Pattern-based) and LLM (Context-based) hybrid approach.
    """

    def __init__(self, use_llm: bool = True):
        """
        Initialize PiiMasker.
        
        Args:
            use_llm: Whether to use LLM for enhanced masking (Names, Addresses).
                     Defaults to True, but will fallback to False if OpenAI API key is missing.
        """
        if not PRESIDIO_AVAILABLE:
            logger.error("Presidio is not installed. PII masking will be disabled.")
            raise ImportError("presidio-analyzer and presidio-anonymizer are required.")

        self.use_llm = use_llm
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Add Korean specific recognizers
        self._add_korean_recognizers()

        # Setup LLM client
        if self.use_llm:
            if OPENAI_AVAILABLE:
                # Check for Custom/Local LLM configuration (from .env)
                # Priority: LOCAL_LLM_* > LLM_* > OPENAI_API_KEY
                
                local_base_url = os.getenv("LOCAL_LLM_BASE_URL") or os.getenv("LLM_BASE_URL")
                local_api_key = os.getenv("LOCAL_LLM_API_KEY") or os.getenv("LLM_API_KEY")
                local_model = os.getenv("LOCAL_LLM_MODEL") or os.getenv("LLM_MODEL")
                
                # Check for OpenAI API Key (fallback)
                openai_api_key = os.getenv("OPENAI_API_KEY")
                
                if local_base_url and local_api_key:
                    # Use Custom/Local LLM
                    logger.info(f"Using Custom/Local LLM at {local_base_url} with model {local_model}")
                    self.llm_client = OpenAI(base_url=local_base_url, api_key=local_api_key)
                    self.llm_model = local_model or "gpt-3.5-turbo" # Fallback model if not specified
                elif openai_api_key:
                    # Use OpenAI
                    logger.info("Using OpenAI API")
                    self.llm_client = OpenAI(api_key=openai_api_key)
                    self.llm_model = "gpt-4o-mini"
                else:
                    logger.warning("No LLM API key or Local LLM config found. LLM masking disabled.")
                    self.use_llm = False
            else:
                logger.warning("OpenAI library not installed. LLM masking disabled.")
                self.use_llm = False

    def _add_korean_recognizers(self):
        """Add Korean specific PII patterns to Presidio registry"""
        
        # Korean Resident Registration Number (RRN)
        korean_rrn = PatternRecognizer(
            supported_entity="KR_RRN",
            patterns=[
                Pattern(name="KR RRN with hyphen", regex=r"\d{6}-\d{7}", score=0.9),
                Pattern(name="KR RRN no hyphen", regex=r"\d{13}(?!\d)", score=0.85),
                Pattern(name="KR RRN with space", regex=r"\d{6}\s+-?\s*\d{7}", score=0.8),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_rrn)

        # Korean Phone Number
        korean_phone = PatternRecognizer(
            supported_entity="KR_PHONE",
            patterns=[
                Pattern(name="Phone with hyphen", regex=r"0\d{1,2}-\d{3,4}-\d{4}", score=0.9),
                Pattern(name="Phone with space", regex=r"0\d{1,2}\s+\d{3,4}\s+\d{4}", score=0.85),
                Pattern(name="Phone no separator", regex=r"0\d{9,10}(?!\d)", score=0.75),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_phone)

        # Korean Bank Account (Generic pattern)
        korean_account = PatternRecognizer(
            supported_entity="KR_ACCOUNT",
            patterns=[
                Pattern(name="Account with hyphen", regex=r"\d{3,4}-\d{2,6}-\d{3,10}", score=0.8),
                Pattern(name="Account no hyphen", regex=r"\d{10,14}(?!\d)", score=0.6),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_account)

        # Business Registration Number (BRN)
        korean_brn = PatternRecognizer(
            supported_entity="KR_BRN",
            patterns=[
                Pattern(name="BRN with hyphen", regex=r"\d{3}-\d{2}-\d{5}", score=0.9),
                Pattern(name="BRN no hyphen", regex=r"\d{10}(?!\d)", score=0.7),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_brn)

    def mask_document(self, text: str) -> MaskingResult:
        """
        Mask PII in the given text.
        
        Args:
            text: The text to mask.
            
        Returns:
            MaskingResult object containing masked text and metadata.
        """
        start_time = time.time()
        
        # Step 1: Presidio Pattern-based Masking
        # We use 'en' language because our custom recognizers are regex-based and work regardless of language setting,
        # and the default model is usually en_core_web_lg.
        analyzer_results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=["KR_RRN", "KR_PHONE", "EMAIL_ADDRESS", "KR_ACCOUNT", "KR_BRN"]
        )

        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results
        )
        
        masked_text = anonymized_result.text
        
        # Collect detected entities from Presidio
        detected_entities = {}
        for result in analyzer_results:
            entity_type = result.entity_type
            if entity_type not in detected_entities:
                detected_entities[entity_type] = []
            # Extract the actual text that was detected (from original text)
            detected_entities[entity_type].append(text[result.start:result.end])

        # Step 2: LLM Context-based Masking (Optional)
        if self.use_llm:
            try:
                llm_masked_text, llm_entities = self._llm_enhance_masking(masked_text)
                masked_text = llm_masked_text
                
                # Merge LLM detected entities
                for entity_type, items in llm_entities.items():
                    if entity_type not in detected_entities:
                        detected_entities[entity_type] = []
                    detected_entities[entity_type].extend(items)
                    
            except Exception as e:
                logger.error(f"LLM masking failed: {e}")
                # Fallback to just Presidio result
        
        processing_time = time.time() - start_time
        
        return MaskingResult(
            masked_text=masked_text,
            detected_entities=detected_entities,
            processing_time=processing_time,
            method="presidio_llm_hybrid" if self.use_llm else "presidio_only"
        )

    def _llm_enhance_masking(self, presidio_masked_text: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Use LLM to mask additional PII (Names, Addresses) that Presidio might miss.
        """
        # Truncate text if too long to avoid token limits (rudimentary handling)
        # In a real production system, we'd chunk this properly.
        # For now, we process the first 4000 chars as a safety measure or assume reasonable document size.
        # If text is very long, we might only mask the beginning or need a loop.
        # Let's assume reasonable page-level chunks for now.
        
        prompt = f"""You are a Korean PII Masking Expert.
Presidio has already masked patterns like RRN, Phone, Email.
Your job is to mask **Names** and **Specific Addresses** that were missed.

## Rules
1. **Mask**:
   - Real Korean Names (2-4 chars) -> [이름_1], [이름_2]...
   - Specific Addresses (Street/Building) -> [주소_1], [주소_2]...
2. **Do NOT Mask**:
   - Roles (대표이사, 임대인, 변호사)
   - General Nouns (회사, 아파트, 은행)
   - Legal Terms (계약금, 보증금)
   - Already masked tags (<KR_RRN>, <EMAIL_ADDRESS>)

## Input Text
{presidio_masked_text[:4000]}

## Output
Return ONLY the fully masked text. Do not add explanations. Maintain original formatting.
"""

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for PII masking."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=4000
        )
        
        llm_masked = response.choices[0].message.content.strip()
        
        # Extract what was masked by LLM (simple heuristic)
        llm_entities = {}
        
        name_count = len(re.findall(r'\[이름_\d+\]', llm_masked))
        if name_count > 0:
            llm_entities["PERSON_NAME"] = [f"Detected {name_count} names"]
            
        addr_count = len(re.findall(r'\[주소_\d+\]', llm_masked))
        if addr_count > 0:
            llm_entities["ADDRESS"] = [f"Detected {addr_count} addresses"]
            
        # If the text was truncated, append the rest of the original text
        if len(presidio_masked_text) > 4000:
            llm_masked += presidio_masked_text[4000:]
            
        return llm_masked, llm_entities

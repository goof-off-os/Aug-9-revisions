#!/usr/bin/env python3
"""
ProposalOS Extraction Service
==============================
Unified extraction service for all document types

This module consolidates extraction logic from:
- orchestrator_production.py (RFP extraction)
- orchestrator_enhanced.py (conversation extraction)
- orchestrator_procurement_enhanced.py (procurement extraction)
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from enum import Enum

import google.generativeai as genai
from pydantic import BaseModel, Field, validator, ValidationError

from config import get_config, Config
from circuit_breakers import get_gemini_breaker, with_circuit_breaker, ServiceName

logger = logging.getLogger(__name__)


# ============ EXTRACTION SCHEMAS ============

class Regulation(BaseModel):
    """Regulation reference"""
    family: str = Field(..., regex=r'^(FAR|DFARS|CAS|Agency|Other)$')
    section: str

class Locator(BaseModel):
    """Document location reference"""
    document: str
    section: Optional[str] = None
    page: Optional[int] = None
    lines: Optional[str] = None

class ExtractedFact(BaseModel):
    """Single extracted fact with validation"""
    element: str = Field(..., regex=r'^(Travel|Materials|Subcontracts|Fringe|Overhead|G&A|ODC|Fee/Profit|Ambiguous)$')
    classification: str = Field(..., regex=r'^(direct|indirect|fee|ambiguous)$')
    regulation: Regulation
    citation_text: str = Field(..., max_length=300)
    locator: Locator
    confidence: float = Field(..., ge=0.0, le=1.0)
    ambiguity_reason: Optional[str] = None
    
    @validator('ambiguity_reason')
    def validate_ambiguity(cls, v, values):
        """Ensure ambiguity_reason is set when classification is ambiguous"""
        if values.get('classification') == 'ambiguous' and not v:
            raise ValueError("ambiguity_reason required when classification is 'ambiguous'")
        return v

class ExtractionResponse(BaseModel):
    """Response from extraction service"""
    facts: List[ExtractedFact] = []
    metadata: Optional[Dict[str, Any]] = None


# ============ POST-PROCESSOR ============

class FactValidator:
    """Validates and repairs extracted facts"""
    
    # Element to allowed regulation patterns
    ALLOWED_REGULATIONS = {
        "Travel": [re.compile(r"^(?:31\.205-46|231\.205-46)($|[^\d])")],
        "Materials": [re.compile(r"^31\.205-26($|[^\d])")],
        "Subcontracts": [re.compile(r"^(?:44\.\d+|15\.404-3|244\.\d+)")],
        "Fringe": [re.compile(r"^31\.205-6"), re.compile(r"^415($|[^\d])")],
        "Overhead": [re.compile(r"^31\.203($|[^\d])"), re.compile(r"^418($|[^\d])")],
        "G&A": [re.compile(r"^410($|[^\d])")],
        "ODC": [re.compile(r"^31\.205-\d+")],
        "Fee/Profit": [re.compile(r"^15\.404-4"), re.compile(r"^215\.404-4")]
    }
    
    GENERIC_ALLOWABILITY = re.compile(r"^31\.201-2($|[^\d])")
    
    @staticmethod
    def word_count(text: str) -> int:
        """Count words in text"""
        return len(re.findall(r"\b\w+\b", text or ""))
    
    def is_regulation_allowed(self, element: str, family: str, section: str) -> bool:
        """Check if regulation is allowed for element"""
        section = (section or "").strip()
        if not section:
            return False
        
        # Normalize prefixes
        if family.upper() == "CAS":
            section = re.sub(r"^CAS[\s-]*", "", section, flags=re.I)
        if family.upper() == "DFARS" and re.match(r"^\d", section):
            section = f"2{section}" if not section.startswith("2") else section
        
        patterns = self.ALLOWED_REGULATIONS.get(element, [])
        return any(pat.search(section) for pat in patterns)
    
    def repair_generic_allowability(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """Repair facts with only generic allowability"""
        reg = fact.get("regulation", {}) or {}
        fam = (reg.get("family") or "").upper()
        sec = (reg.get("section") or "").strip()
        
        if fam == "FAR" and self.GENERIC_ALLOWABILITY.match(sec):
            fact["classification"] = "ambiguous"
            fact["element"] = "Ambiguous"
            fact["ambiguity_reason"] = "Only FAR 31.201-2 (general allowability) cited"
        
        return fact
    
    def validate_and_repair(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and repair extracted facts"""
        cleaned = []
        seen = set()
        
        for fact in facts or []:
            # Check word count
            if self.word_count(fact.get("citation_text", "")) > 25:
                continue
            
            # Check required fields
            if not all(fact.get(f) for f in ["element", "classification", "regulation"]):
                continue
            
            # Repair generic allowability
            fact = self.repair_generic_allowability(fact)
            
            # Check allowed regulations
            if fact.get("element") != "Ambiguous":
                reg = fact.get("regulation", {})
                if not self.is_regulation_allowed(
                    fact["element"],
                    reg.get("family", ""),
                    reg.get("section", "")
                ):
                    # Special case for ODC
                    if fact["element"] == "ODC" and self.GENERIC_ALLOWABILITY.match(reg.get("section", "")):
                        fact["element"] = "Ambiguous"
                        fact["classification"] = "ambiguous"
                        fact["ambiguity_reason"] = "ODC requires specific 31.205-x section"
                    else:
                        continue
            
            # Deduplicate
            key = (
                fact.get("element"),
                fact.get("classification"),
                fact.get("regulation", {}).get("family"),
                fact.get("regulation", {}).get("section"),
                (fact.get("citation_text", "")).strip().lower()
            )
            if key in seen:
                continue
            seen.add(key)
            
            # Check confidence
            if fact.get("confidence", 0) < 0.7 and fact.get("element") != "Ambiguous":
                continue
            
            cleaned.append(fact)
        
        return cleaned


# ============ EXTRACTION SERVICE ============

class ExtractionService:
    """Unified extraction service for all document types"""
    
    def __init__(
        self,
        model: Optional[genai.GenerativeModel] = None,
        fast_model: Optional[genai.GenerativeModel] = None,
        config: Optional[Config] = None
    ):
        """
        Initialize extraction service
        
        Args:
            model: Primary Gemini model for complex extraction
            fast_model: Optional fast model for simple extraction
            config: Configuration object
        """
        self.config = config or get_config()
        self.model = model
        self.fast_model = fast_model or model
        self.validator = FactValidator()
        self.prompts = self._load_prompts()
        
        logger.info("ExtractionService initialized")
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load extraction prompts"""
        prompts = {}
        
        # RFP EoC Extraction prompt
        prompts['rfp_eoc'] = """
SYSTEM
You are a federal cost analyst. Extract only facts that are directly supported by the text. Do not infer.

TASK
From the provided RFP / attachment text, extract cost-element facts and citations with strict JSON ONLY.

OUTPUT FORMAT (strict JSON array)
[
  {
    "element": "Travel" | "Materials" | "Subcontracts" | "Fringe" | "Overhead" | "G&A" | "ODC" | "Fee/Profit" | "Ambiguous",
    "classification": "direct" | "indirect" | "fee" | "ambiguous",
    "regulation": {
      "family": "FAR" | "DFARS" | "CAS" | "Agency" | "Other",
      "section": "e.g., 31.205-46"
    },
    "citation_text": "≤25 words copied verbatim from the source",
    "locator": { "document": "RFP|Attachment|Section", "section": "e.g., L.2.3", "page": 7, "lines": "120-133" },
    "confidence": 0.0-1.0,
    "ambiguity_reason": "string, required only if classification=='ambiguous'"
  }
]

RETURN
JSON only.

RFP TEXT:
"""
        
        # Conversation data extraction prompt
        prompts['conversation'] = """
Extract structured data from the following conversation.

Return a JSON object with:
{
  "data_state": "incomplete" | "partial" | "complete",
  "facts": {
    // Key-value pairs of extracted information
  },
  "follow_up_questions": [
    // Array of questions to ask user
  ],
  "confidence": 0.0-1.0
}

CONVERSATION:
"""
        
        # Procurement validation prompt
        prompts['procurement'] = """
Analyze the following procurement request for compliance issues.

Return a JSON object with:
{
  "is_compliant": true | false,
  "issues": [
    {
      "code": "string",
      "description": "string",
      "severity": "Critical" | "Error" | "Warning" | "Info",
      "regulation": "string"
    }
  ],
  "recommendations": ["string"]
}

PROCUREMENT DATA:
"""
        
        return prompts
    
    async def extract_from_rfp(
        self,
        rfp_text: str,
        use_fast_model: bool = False
    ) -> ExtractionResponse:
        """
        Extract Elements of Cost from RFP text
        
        Args:
            rfp_text: RFP document text
            use_fast_model: Whether to use fast model
            
        Returns:
            ExtractionResponse with validated facts
        """
        model = self.fast_model if use_fast_model else self.model
        if not model:
            raise ValueError("No model configured for extraction")
        
        prompt = self.prompts['rfp_eoc'] + rfp_text
        
        # Call model with circuit breaker
        response_text = await with_circuit_breaker(
            ServiceName.GEMINI,
            self._call_model,
            model,
            prompt,
            fallback="[]"
        )
        
        # Parse JSON response
        try:
            raw_facts = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if match:
                raw_facts = json.loads(match.group())
            else:
                logger.error("No valid JSON in model response")
                raw_facts = []
        
        # Validate and repair facts
        cleaned_facts = self.validator.validate_and_repair(raw_facts)
        
        # Convert to Pydantic models
        validated_facts = []
        for fact_dict in cleaned_facts:
            try:
                fact = ExtractedFact(**fact_dict)
                validated_facts.append(fact)
            except ValidationError as e:
                logger.warning(f"Fact validation failed: {e}")
        
        return ExtractionResponse(
            facts=validated_facts,
            metadata={
                'total_raw': len(raw_facts),
                'total_cleaned': len(cleaned_facts),
                'total_validated': len(validated_facts),
                'extraction_timestamp': datetime.now().isoformat()
            }
        )
    
    async def extract_from_conversation(
        self,
        conversation: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Extract structured data from conversation
        
        Args:
            conversation: List of conversation messages
            
        Returns:
            Extracted data dictionary
        """
        if not self.model:
            raise ValueError("No model configured for extraction")
        
        # Format conversation
        conv_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation
        ])
        
        prompt = self.prompts['conversation'] + conv_text
        
        # Call model with circuit breaker
        response_text = await with_circuit_breaker(
            ServiceName.GEMINI,
            self._call_model,
            self.model,
            prompt,
            fallback='{"data_state": "error", "facts": {}, "follow_up_questions": []}'
        )
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse conversation extraction response")
            return {
                "data_state": "error",
                "facts": {},
                "follow_up_questions": [],
                "error": "Failed to parse model response"
            }
    
    async def validate_procurement(
        self,
        procurement_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate procurement request for compliance
        
        Args:
            procurement_data: Procurement request data
            
        Returns:
            Validation results
        """
        if not self.model:
            raise ValueError("No model configured for extraction")
        
        prompt = self.prompts['procurement'] + json.dumps(procurement_data, indent=2)
        
        # Call model with circuit breaker
        response_text = await with_circuit_breaker(
            ServiceName.GEMINI,
            self._call_model,
            self.model,
            prompt,
            fallback='{"is_compliant": false, "issues": [{"code": "ERROR", "description": "Validation service unavailable", "severity": "Critical"}], "recommendations": []}'
        )
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse procurement validation response")
            return {
                "is_compliant": False,
                "issues": [{
                    "code": "PARSE_ERROR",
                    "description": "Failed to parse validation response",
                    "severity": "Critical"
                }],
                "recommendations": []
            }
    
    async def _call_model(
        self,
        model: genai.GenerativeModel,
        prompt: str
    ) -> str:
        """
        Call Gemini model with error handling
        
        Args:
            model: Gemini model instance
            prompt: Prompt text
            
        Returns:
            Model response text
        """
        try:
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Model call failed: {e}")
            raise
    
    def batch_extract(
        self,
        documents: List[Tuple[str, str]],
        extraction_type: str = "rfp_eoc"
    ) -> List[Dict[str, Any]]:
        """
        Batch extract from multiple documents
        
        Args:
            documents: List of (document_id, document_text) tuples
            extraction_type: Type of extraction to perform
            
        Returns:
            List of extraction results
        """
        results = []
        
        for doc_id, doc_text in documents:
            try:
                if extraction_type == "rfp_eoc":
                    result = asyncio.run(self.extract_from_rfp(doc_text))
                    results.append({
                        'document_id': doc_id,
                        'status': 'success',
                        'facts': [f.dict() for f in result.facts],
                        'metadata': result.metadata
                    })
                else:
                    results.append({
                        'document_id': doc_id,
                        'status': 'error',
                        'error': f"Unknown extraction type: {extraction_type}"
                    })
            except Exception as e:
                logger.error(f"Extraction failed for document {doc_id}: {e}")
                results.append({
                    'document_id': doc_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results


# Singleton instance
_extraction_service: Optional[ExtractionService] = None


def get_extraction_service(
    model: Optional[genai.GenerativeModel] = None,
    fast_model: Optional[genai.GenerativeModel] = None
) -> ExtractionService:
    """Get or create the extraction service singleton"""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService(model, fast_model)
    return _extraction_service


if __name__ == "__main__":
    """Test extraction service"""
    import asyncio
    
    async def test_extraction():
        # Mock model for testing
        class MockModel:
            async def generate_content_async(self, prompt):
                class Response:
                    text = json.dumps([{
                        "element": "Travel",
                        "classification": "direct",
                        "regulation": {"family": "FAR", "section": "31.205-46"},
                        "citation_text": "Travel costs are allowable",
                        "locator": {"document": "RFP", "page": 1},
                        "confidence": 0.95
                    }])
                return Response()
        
        # Create service with mock model
        service = ExtractionService(model=MockModel())
        
        # Test RFP extraction
        result = await service.extract_from_rfp("Sample RFP text with travel requirements")
        print(f"Extracted {len(result.facts)} facts")
        for fact in result.facts:
            print(f"  - {fact.element}: {fact.citation_text}")
        
        # Test conversation extraction
        conversation = [
            {"role": "user", "content": "We need travel for 5 people"},
            {"role": "assistant", "content": "What are the destinations?"}
        ]
        conv_result = await service.extract_from_conversation(conversation)
        print(f"Conversation state: {conv_result.get('data_state')}")
    
    asyncio.run(test_extraction())
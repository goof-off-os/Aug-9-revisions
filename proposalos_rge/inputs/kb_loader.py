# proposalos_rge/inputs/kb_loader.py
from pathlib import Path
import json
from typing import List, Optional, Dict, Any
from ..schemas import KBFact, UnifiedPayload, UIInputs, RegulatorySupport, SourceRef


def load_kb_to_payload(kb_path: str, ui: UIInputs) -> UnifiedPayload:
    """
    Load KB JSON and adapt to UnifiedPayload.facts
    
    Args:
        kb_path: Path to KB_cleaned.json
        ui: UI inputs from user
        
    Returns:
        UnifiedPayload with facts loaded
    """
    data = json.loads(Path(kb_path).read_text())
    facts = []
    
    for f in data.get("facts", []):
        # Convert regulatory support if present
        reg_support = []
        if "regulatory_support" in f:
            for reg in f["regulatory_support"]:
                if isinstance(reg, dict):
                    reg_support.append(RegulatorySupport(**reg))
        
        # Create source reference if present
        source = None
        if "source" in f and f["source"]:
            source = SourceRef(**f["source"])
        
        # Create KBFact
        fact = KBFact(
            fact_id=f.get("fact_id"),
            element=f.get("element", "Unknown"),
            classification=f.get("classification", "ambiguous"),
            rfp_relevance=f.get("rfp_relevance"),
            regulatory_support=reg_support,
            notes=f.get("notes"),
            source=source,
            timestamp=f.get("timestamp"),
            confidence=f.get("confidence")
        )
        facts.append(fact)
    
    return UnifiedPayload(ui=ui, facts=facts)


def load_rfp_extraction_to_payload(
    extraction_response: Dict[str, Any],
    ui: UIInputs
) -> UnifiedPayload:
    """
    Convert extraction service response to UnifiedPayload
    
    Args:
        extraction_response: Response from extraction service
        ui: UI inputs
        
    Returns:
        UnifiedPayload with facts from extraction
    """
    facts = []
    
    for fact_data in extraction_response.get("facts", []):
        # Convert extraction fact to KBFact
        reg_support = []
        if "regulation" in fact_data:
            reg = fact_data["regulation"]
            reg_support.append(RegulatorySupport(
                reg_title=reg.get("family", ""),
                reg_section=reg.get("section", ""),
                quote=fact_data.get("citation_text", ""),
                confidence=fact_data.get("confidence", 0.0)
            ))
        
        source = None
        if "locator" in fact_data:
            loc = fact_data["locator"]
            source = SourceRef(
                doc_id=loc.get("document"),
                section=loc.get("section"),
                title=f"Page {loc.get('page', 'N/A')}"
            )
        
        fact = KBFact(
            element=fact_data.get("element", "Unknown"),
            classification=fact_data.get("classification", "ambiguous"),
            regulatory_support=reg_support,
            source=source,
            confidence=fact_data.get("confidence", 0.0)
        )
        facts.append(fact)
    
    return UnifiedPayload(ui=ui, facts=facts)
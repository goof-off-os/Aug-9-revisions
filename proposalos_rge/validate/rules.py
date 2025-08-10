# proposalos_rge/validate/rules.py
from typing import Tuple, List, Dict, Any
from ..schemas import UnifiedPayload, AuditEntry, KBFact
import re


def validate_facts(facts: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """
    Validate facts for compliance and consistency
    
    This is a simplified version - the full version would import from
    compile_reports_refactor.py if available
    
    Args:
        facts: List of fact dictionaries
        
    Returns:
        Tuple of (warnings, errors)
    """
    warnings = []
    errors = []
    
    for fact in facts:
        element = fact.get("element", "")
        classification = fact.get("classification", "")
        
        # Check element-classification consistency
        if element in ["Travel", "Materials", "Subcontracts", "ODC"]:
            if classification != "direct":
                warnings.append(
                    f"{element} should typically be classified as 'direct', not '{classification}'"
                )
        
        if element in ["Overhead", "G&A", "Fringe"]:
            if classification != "indirect":
                warnings.append(
                    f"{element} should typically be classified as 'indirect', not '{classification}'"
                )
        
        if element == "Fee/Profit":
            if classification != "fee":
                warnings.append(
                    f"Fee/Profit should be classified as 'fee', not '{classification}'"
                )
        
        # Check regulatory support
        reg_support = fact.get("regulatory_support", [])
        if not reg_support and element != "Ambiguous":
            warnings.append(f"{element} fact lacks regulatory support")
        
        # Check confidence
        confidence = fact.get("confidence", 0)
        if confidence < 0.5 and element != "Ambiguous":
            warnings.append(f"{element} fact has low confidence ({confidence})")
    
    # Check for duplicate elements
    element_counts = {}
    for fact in facts:
        element = fact.get("element", "Unknown")
        element_counts[element] = element_counts.get(element, 0) + 1
    
    for element, count in element_counts.items():
        if count > 5:  # Arbitrary threshold
            warnings.append(f"Unusually high number of {element} facts ({count})")
    
    return warnings, errors


def run_validators(payload: UnifiedPayload) -> UnifiedPayload:
    """
    Run all validation rules on the payload
    
    Args:
        payload: Unified payload to validate
        
    Returns:
        Payload with audit entries added
    """
    # Validate facts
    warnings, errors = validate_facts([f.dict() for f in payload.facts])
    
    for w in warnings:
        payload.audit.validations.append(AuditEntry(
            kind="warning",
            code="fact_validation",
            message=w
        ))
    
    for e in errors:
        payload.audit.validations.append(AuditEntry(
            kind="error",
            code="fact_consistency",
            message=e
        ))
    
    # Validate allocations
    _validate_allocations(payload)
    
    # Validate regulatory compliance
    _validate_regulatory_compliance(payload)
    
    # Validate mathematical consistency
    _validate_math_consistency(payload)
    
    return payload


def _validate_allocations(payload: UnifiedPayload) -> None:
    """Validate allocation data"""
    
    if not payload.allocations:
        if payload.ui.level != "Total":
            payload.audit.validations.append(AuditEntry(
                kind="warning",
                code="no_allocations",
                message=f"No allocations provided for level '{payload.ui.level}'"
            ))
        return
    
    # Check for negative values
    for alloc in payload.allocations:
        if alloc.cost and alloc.cost < 0:
            payload.audit.validations.append(AuditEntry(
                kind="error",
                code="negative_cost",
                message=f"Negative cost in allocation: {alloc.fy} {alloc.task or 'Unknown'}"
            ))
        
        if alloc.hours < 0:
            payload.audit.validations.append(AuditEntry(
                kind="error",
                code="negative_hours",
                message=f"Negative hours in allocation: {alloc.fy} {alloc.task or 'Unknown'}"
            ))
        
        # Check hours-rate-cost consistency
        if alloc.hours > 0 and alloc.rate and alloc.cost:
            expected_cost = alloc.hours * alloc.rate
            if abs(expected_cost - alloc.cost) > 0.01:  # Allow small rounding errors
                payload.audit.validations.append(AuditEntry(
                    kind="warning",
                    code="cost_calculation",
                    message=f"Cost mismatch in {alloc.fy}: {alloc.hours}h × ${alloc.rate} ≠ ${alloc.cost}",
                    context={
                        "hours": str(alloc.hours),
                        "rate": str(alloc.rate),
                        "expected": str(expected_cost),
                        "actual": str(alloc.cost)
                    }
                ))


def _validate_regulatory_compliance(payload: UnifiedPayload) -> None:
    """Validate regulatory compliance"""
    
    # Check FAR/DFARS citations
    for fact in payload.facts:
        for reg in fact.regulatory_support:
            if reg.reg_section:
                # Validate FAR format
                if reg.reg_title == "FAR":
                    if not re.match(r'^\d+\.\d+(-\d+)?', reg.reg_section):
                        payload.audit.validations.append(AuditEntry(
                            kind="warning",
                            code="invalid_far_format",
                            message=f"Invalid FAR section format: {reg.reg_section}"
                        ))
                
                # Validate DFARS format
                elif reg.reg_title == "DFARS":
                    if not re.match(r'^\d{3}\.\d+(-\d+)?', reg.reg_section):
                        payload.audit.validations.append(AuditEntry(
                            kind="warning",
                            code="invalid_dfars_format",
                            message=f"Invalid DFARS section format: {reg.reg_section}"
                        ))
    
    # Check for required elements based on contract type
    required_elements = {
        "CPFF": ["Direct Labor", "Fee/Profit"],
        "FFP": ["Direct Labor"],
        "T&M": ["Direct Labor", "Materials"]
    }
    
    if payload.ui.contract_type in required_elements:
        existing_elements = {f.element for f in payload.facts}
        missing = set(required_elements[payload.ui.contract_type]) - existing_elements
        
        for element in missing:
            payload.audit.validations.append(AuditEntry(
                kind="warning",
                code="missing_required_element",
                message=f"{payload.ui.contract_type} contract missing required element: {element}"
            ))


def _validate_math_consistency(payload: UnifiedPayload) -> None:
    """Validate mathematical consistency"""
    
    if not payload.allocations:
        return
    
    # Check total by fiscal year
    fy_totals = {}
    for alloc in payload.allocations:
        if alloc.cost:
            fy_totals[alloc.fy] = fy_totals.get(alloc.fy, 0) + alloc.cost
    
    # If we have a fee element, check it's reasonable (typically 5-15% for CPFF)
    if payload.ui.contract_type == "CPFF":
        fee_facts = [f for f in payload.facts if f.element == "Fee/Profit"]
        if fee_facts and payload.ui.fee_value:
            total_cost = sum(fy_totals.values())
            expected_fee = total_cost * (payload.ui.fee_value / 100)
            
            # This is a simplified check - real implementation would be more sophisticated
            if expected_fee > total_cost * 0.15:
                payload.audit.validations.append(AuditEntry(
                    kind="warning",
                    code="high_fee_percentage",
                    message=f"Fee percentage seems high: {payload.ui.fee_value}%"
                ))
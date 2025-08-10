# proposalos_rge/normalize/builder.py
from typing import Optional, List, Dict, Any
from ..schemas import UnifiedPayload, UIInputs, Allocation, KBFact, AuditEntry
from ..inputs.ui_adapter import (
    create_allocations_from_travel,
    create_allocations_from_labor,
    create_assumptions_from_facts,
    create_hefs_from_config,
    create_gfx_from_rfp
)


def build_unified_payload(
    ui: UIInputs,
    base_payload: UnifiedPayload,
    additional_data: Optional[Dict[str, Any]] = None
) -> UnifiedPayload:
    """
    Build and normalize unified payload
    
    For MVP: merges UI with base payload
    Later: merge UI + RFP + KB + additional data sources
    
    Args:
        ui: User interface inputs
        base_payload: Base payload with facts
        additional_data: Optional additional data (travel, labor, etc.)
        
    Returns:
        Normalized UnifiedPayload
    """
    payload = base_payload.copy(deep=True)
    payload.ui = ui
    
    if additional_data:
        # Add travel allocations if present
        if "travel" in additional_data:
            travel_allocations = create_allocations_from_travel(
                additional_data["travel"],
                ui.fiscal_years[0] if ui.fiscal_years else "FY2025"
            )
            payload.allocations.extend(travel_allocations)
        
        # Add labor allocations if present
        if "labor" in additional_data:
            labor_allocations = create_allocations_from_labor(
                additional_data["labor"],
                ui.fiscal_years
            )
            payload.allocations.extend(labor_allocations)
        
        # Add RFP metadata if present
        if "rfp" in additional_data:
            from ..schemas import RFPMeta
            payload.rfp = RFPMeta(**additional_data["rfp"])
            
            # Extract GFX from RFP
            gfx_items = create_gfx_from_rfp(additional_data["rfp"])
            payload.gfx.extend(gfx_items)
    
    # Generate assumptions from facts if not present
    if not payload.assumptions and payload.facts:
        payload.assumptions = create_assumptions_from_facts(
            [f.dict() for f in payload.facts]
        )
    
    # Generate default HEFs if not present
    if not payload.hefs:
        payload.hefs = create_hefs_from_config()
    
    # Detect conflicts between UI and payload
    _detect_conflicts(payload)
    
    return payload


def _detect_conflicts(payload: UnifiedPayload) -> None:
    """
    Detect conflicts between UI selections and payload data
    
    Args:
        payload: Unified payload to check
    """
    # Check contract type conflicts
    if payload.ui.contract_type and payload.rfp:
        rfp_contract_type = getattr(payload.rfp, "contract_type", None)
        if rfp_contract_type and rfp_contract_type != payload.ui.contract_type:
            payload.audit.conflicts.append(AuditEntry(
                kind="warning",
                code="CONTRACT_TYPE_MISMATCH",
                message=f"UI contract type ({payload.ui.contract_type}) differs from RFP ({rfp_contract_type})",
                context={
                    "ui_value": payload.ui.contract_type,
                    "rfp_value": rfp_contract_type
                }
            ))
    
    # Check fiscal year coverage
    if payload.ui.fiscal_years and payload.allocations:
        allocation_fys = set(a.fy for a in payload.allocations)
        requested_fys = set(payload.ui.fiscal_years)
        
        missing_fys = requested_fys - allocation_fys
        if missing_fys:
            payload.audit.conflicts.append(AuditEntry(
                kind="warning",
                code="MISSING_FY_DATA",
                message=f"No allocation data for fiscal years: {', '.join(missing_fys)}",
                context={
                    "requested": list(requested_fys),
                    "available": list(allocation_fys)
                }
            ))
    
    # Check for required elements based on contract type
    if payload.ui.contract_type == "CPFF":
        has_fee = any(f.element == "Fee/Profit" for f in payload.facts)
        if not has_fee:
            payload.audit.validations.append(AuditEntry(
                kind="warning",
                code="MISSING_FEE_ELEMENT",
                message="CPFF contract type but no Fee/Profit element found",
                context={"contract_type": "CPFF"}
            ))


def merge_payloads(payloads: List[UnifiedPayload]) -> UnifiedPayload:
    """
    Merge multiple payloads into one
    
    Args:
        payloads: List of payloads to merge
        
    Returns:
        Merged UnifiedPayload
    """
    if not payloads:
        raise ValueError("No payloads to merge")
    
    if len(payloads) == 1:
        return payloads[0]
    
    # Start with first payload as base
    merged = payloads[0].copy(deep=True)
    
    # Merge facts, allocations, etc. from other payloads
    for payload in payloads[1:]:
        # Merge facts (avoid duplicates based on fact_id)
        existing_fact_ids = {f.fact_id for f in merged.facts if f.fact_id}
        for fact in payload.facts:
            if not fact.fact_id or fact.fact_id not in existing_fact_ids:
                merged.facts.append(fact)
        
        # Merge allocations
        merged.allocations.extend(payload.allocations)
        
        # Merge assumptions
        merged.assumptions.extend(payload.assumptions)
        
        # Merge audit entries
        merged.audit.validations.extend(payload.audit.validations)
        merged.audit.conflicts.extend(payload.audit.conflicts)
    
    return merged
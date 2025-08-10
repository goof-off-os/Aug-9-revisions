# proposalos_rge/inputs/ui_adapter.py
from typing import Dict, Any, List, Optional
from ..schemas import UIInputs, Allocation, Assumption, HEF, GFX


def adapt_ui_request(request_data: Dict[str, Any]) -> UIInputs:
    """
    Adapt raw UI request data to UIInputs schema
    
    Args:
        request_data: Raw request from frontend
        
    Returns:
        Validated UIInputs
    """
    return UIInputs(
        mode=request_data.get("mode"),
        level=request_data.get("level", "Total"),
        fee_method=request_data.get("fee_method"),
        fee_value=request_data.get("fee_value"),
        contract_type=request_data.get("contract_type", "CPFF"),
        prime_or_sub=request_data.get("prime_or_sub", "prime"),
        customer_id=request_data.get("customer_id"),
        fiscal_years=request_data.get("fiscal_years", ["FY2025", "FY2026"])
    )


def create_allocations_from_travel(
    travel_data: List[Dict[str, Any]],
    fiscal_year: str = "FY2025"
) -> List[Allocation]:
    """
    Convert travel calculator data to allocations
    
    Args:
        travel_data: List of travel entries
        fiscal_year: Target fiscal year
        
    Returns:
        List of Allocation objects
    """
    allocations = []
    
    for trip in travel_data:
        allocation = Allocation(
            fy=fiscal_year,
            task="Travel",
            clin=trip.get("clin"),
            wbs=trip.get("wbs"),
            hours=0.0,  # Travel doesn't have hours
            cost=trip.get("total_cost", 0.0)
        )
        allocations.append(allocation)
    
    return allocations


def create_allocations_from_labor(
    labor_data: Dict[str, Any],
    fiscal_years: List[str]
) -> List[Allocation]:
    """
    Convert labor estimates to allocations
    
    Args:
        labor_data: Labor estimate data
        fiscal_years: List of fiscal years to allocate across
        
    Returns:
        List of Allocation objects
    """
    allocations = []
    
    # Distribute labor evenly across fiscal years (simplified)
    num_years = len(fiscal_years) if fiscal_years else 1
    
    for resource_id, resource_data in labor_data.get("resources", {}).items():
        total_hours = resource_data.get("total_hours", 0)
        hourly_rate = resource_data.get("rate", 150.0)  # Default rate
        
        hours_per_year = total_hours / num_years
        
        for fy in fiscal_years:
            allocation = Allocation(
                fy=fy,
                task=resource_data.get("task", "Direct Labor"),
                clin=resource_data.get("clin"),
                wbs=resource_data.get("wbs"),
                ipt=resource_data.get("ipt"),
                hours=hours_per_year,
                rate=hourly_rate,
                cost=hours_per_year * hourly_rate
            )
            allocations.append(allocation)
    
    return allocations


def create_assumptions_from_facts(facts: List[Dict[str, Any]]) -> List[Assumption]:
    """
    Extract assumptions from fact notes
    
    Args:
        facts: List of fact dictionaries
        
    Returns:
        List of Assumption objects
    """
    assumptions = []
    
    for fact in facts:
        if fact.get("notes"):
            assumption = Assumption(
                text=fact["notes"],
                source=f"Element: {fact.get('element', 'Unknown')}"
            )
            assumptions.append(assumption)
    
    # Add standard assumptions
    assumptions.extend([
        Assumption(
            text="All costs are in base year dollars unless otherwise noted",
            source="Standard"
        ),
        Assumption(
            text="Labor rates include all applicable burdens and overheads",
            source="Standard"
        ),
        Assumption(
            text="Travel costs based on current GSA per diem rates",
            source="GSA"
        )
    ])
    
    return assumptions


def create_hefs_from_config(
    base_year: int = 2025,
    num_years: int = 5,
    escalation_rate: float = 0.03
) -> List[HEF]:
    """
    Create default Human Effort Factors
    
    Args:
        base_year: Base year for factors
        num_years: Number of years to project
        escalation_rate: Annual escalation rate
        
    Returns:
        List of HEF objects
    """
    series = {}
    
    for i in range(num_years):
        year = base_year + i
        factor = (1 + escalation_rate) ** i
        series[f"FY{year}"] = round(factor, 3)
    
    return [HEF(basis_year=base_year, series=series)]


def create_gfx_from_rfp(rfp_data: Dict[str, Any]) -> List[GFX]:
    """
    Extract GFE/GFX from RFP data
    
    Args:
        rfp_data: RFP metadata
        
    Returns:
        List of GFX objects
    """
    gfx_list = []
    
    # Check for standard GFE items
    if rfp_data.get("includes_gfe", False):
        gfx_list.append(GFX(
            type="GFE",
            description="Standard Government Furnished Equipment",
            provided_by=rfp_data.get("customer", "Government")
        ))
    
    # Add any specific GFX mentioned
    for item in rfp_data.get("gfx_items", []):
        gfx_list.append(GFX(
            type=item.get("type", "GFX"),
            description=item.get("description", ""),
            provided_by=item.get("provided_by")
        ))
    
    return gfx_list
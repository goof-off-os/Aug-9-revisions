#!/usr/bin/env python3
"""
ProposalOS RGE - Example Usage Script
======================================
Demonstrates how to use the Report Generation Engine with DFARS templates
"""

import json
from pathlib import Path
from datetime import datetime

# Import RGE components
from proposalos_rge.schemas import (
    UIInputs, 
    UnifiedPayload, 
    KBFact, 
    Allocation,
    RegulatorySupport,
    RFPMeta,
    Assumption
)
from proposalos_rge.api.endpoints import PreviewBody, preview, generate, GenerateBody
from proposalos_rge.inputs.kb_loader import load_kb_to_payload
from proposalos_rge.normalize.builder import build_unified_payload
from proposalos_rge.validate.rules import run_validators


def example_1_basic_dfars_checklist():
    """Example 1: Generate DFARS checklist from KB file"""
    print("\n" + "="*60)
    print("EXAMPLE 1: DFARS Checklist from KB")
    print("="*60)
    
    # Create UI inputs
    ui = UIInputs(
        contract_type="CPFF",
        fiscal_years=["FY2025", "FY2026"],
        level="Task",
        customer_id="USSF",
        prime_or_sub="prime"
    )
    
    # Option A: Load from KB file (if you have KB_cleaned.json)
    kb_path = "/Users/carolinehusebo/Desktop/Agents writing reports/RFP_Discovery_System/KB_cleaned.json"
    if Path(kb_path).exists():
        # Generate DFARS checklist
        preview_body = PreviewBody(
            ui=ui,
            kb_path=kb_path,
            template="DFARS_CHECKLIST"
        )
        result = preview(preview_body)
        
        print("\nDFARS Checklist Generated:")
        print("-" * 40)
        for section in result["sections"]:
            print(section["content"])
    else:
        print(f"KB file not found at {kb_path}")
        print("Using synthetic data instead...")
        example_2_synthetic_data()


def example_2_synthetic_data():
    """Example 2: Generate reports with synthetic data"""
    print("\n" + "="*60)
    print("EXAMPLE 2: DFARS Reports with Synthetic Data")
    print("="*60)
    
    # Create UI inputs
    ui = UIInputs(
        contract_type="CPFF",
        fiscal_years=["FY2025", "FY2026", "FY2027"],
        level="Task",
        customer_id="USSF",
        prime_or_sub="prime",
        fee_method="target_percent",
        fee_value=8.0
    )
    
    # Create synthetic facts
    facts = [
        KBFact(
            element="Direct Labor",
            classification="direct",
            regulatory_support=[
                RegulatorySupport(
                    reg_title="FAR",
                    reg_section="31.202",
                    quote="Direct labor costs are allowable",
                    confidence=0.95
                )
            ],
            confidence=0.9
        ),
        KBFact(
            element="Travel",
            classification="direct",
            regulatory_support=[
                RegulatorySupport(
                    reg_title="FAR",
                    reg_section="31.205-46",
                    quote="Travel costs are allowable when reasonable",
                    confidence=0.9
                )
            ],
            confidence=0.85
        ),
        KBFact(
            element="Materials",
            classification="direct",
            regulatory_support=[
                RegulatorySupport(
                    reg_title="FAR",
                    reg_section="31.205-26",
                    quote="Material costs are allowable",
                    confidence=0.88
                )
            ],
            confidence=0.87
        ),
        KBFact(
            element="Subcontracts",
            classification="direct",
            regulatory_support=[
                RegulatorySupport(
                    reg_title="FAR",
                    reg_section="44.201",
                    quote="Subcontract costs subject to review",
                    confidence=0.82
                )
            ],
            confidence=0.8
        ),
        KBFact(
            element="Overhead",
            classification="indirect",
            regulatory_support=[
                RegulatorySupport(
                    reg_title="FAR",
                    reg_section="31.203",
                    quote="Indirect costs allocated per CAS",
                    confidence=0.91
                )
            ],
            confidence=0.9
        ),
        KBFact(
            element="Fee/Profit",
            classification="fee",
            regulatory_support=[
                RegulatorySupport(
                    reg_title="FAR",
                    reg_section="15.404-4",
                    quote="Fee determination per weighted guidelines",
                    confidence=0.95
                )
            ],
            confidence=0.93
        )
    ]
    
    # Create synthetic allocations
    allocations = [
        # FY2025
        Allocation(fy="FY2025", task="Direct Labor", hours=10000, rate=150, cost=1500000),
        Allocation(fy="FY2025", task="Travel", cost=75000),
        Allocation(fy="FY2025", task="Materials", cost=250000),
        Allocation(fy="FY2025", task="Subcontracts", cost=500000),
        Allocation(fy="FY2025", task="Overhead", cost=450000),
        Allocation(fy="FY2025", task="G&A", cost=137500),
        Allocation(fy="FY2025", task="Fee/Profit", cost=233000),
        
        # FY2026
        Allocation(fy="FY2026", task="Direct Labor", hours=12000, rate=155, cost=1860000),
        Allocation(fy="FY2026", task="Travel", cost=80000),
        Allocation(fy="FY2026", task="Materials", cost=300000),
        Allocation(fy="FY2026", task="Subcontracts", cost=600000),
        Allocation(fy="FY2026", task="Overhead", cost=558000),
        Allocation(fy="FY2026", task="G&A", cost=169900),
        Allocation(fy="FY2026", task="Fee/Profit", cost=285456),
        
        # FY2027
        Allocation(fy="FY2027", task="Direct Labor", hours=8000, rate=160, cost=1280000),
        Allocation(fy="FY2027", task="Travel", cost=60000),
        Allocation(fy="FY2027", task="Materials", cost=200000),
        Allocation(fy="FY2027", task="Subcontracts", cost=400000),
        Allocation(fy="FY2027", task="Overhead", cost=384000),
        Allocation(fy="FY2027", task="G&A", cost=116200),
        Allocation(fy="FY2027", task="Fee/Profit", cost=195216),
    ]
    
    # Create RFP metadata
    rfp = RFPMeta(
        rfp_id="FA8750-25-R-0001",
        title="Advanced Satellite Communications System",
        customer="USSF Space Systems Command",
        url="https://sam.gov/opp/FA8750-25-R-0001"
    )
    
    # Create assumptions
    assumptions = [
        Assumption(text="All labor rates include current fringe benefits", source="HR Policy"),
        Assumption(text="Travel costs based on current GSA per diem rates", source="GSA.gov"),
        Assumption(text="3% annual escalation applied to base rates", source="IHS Markit"),
        Assumption(text="Subcontract costs include 5% management fee", source="Company Policy")
    ]
    
    # Build unified payload
    payload = UnifiedPayload(
        ui=ui,
        rfp=rfp,
        facts=facts,
        allocations=allocations,
        assumptions=assumptions
    )
    
    # Validate payload
    payload = run_validators(payload)
    
    # Generate DFARS Checklist
    print("\n1. GENERATING DFARS CHECKLIST")
    print("-" * 40)
    preview_body = PreviewBody(
        ui=ui,
        payload=payload,
        template="DFARS_CHECKLIST"
    )
    checklist_result = preview(preview_body)
    
    for section in checklist_result["sections"]:
        print(section["content"])
    
    # Generate DFARS Cover Page
    print("\n2. GENERATING DFARS COVER PAGE")
    print("-" * 40)
    preview_body.template = "DFARS_COVER_PAGE"
    cover_result = preview(preview_body)
    
    for section in cover_result["sections"]:
        print(section["content"])
    
    # Generate Annual FY Report
    print("\n3. GENERATING ANNUAL FY REPORT")
    print("-" * 40)
    preview_body.template = "ANNUAL_FY"
    annual_result = preview(preview_body)
    
    for section in annual_result["sections"]:
        print(section["content"][:500] + "...")  # Truncate for display
    
    # Show audit results
    print("\n4. VALIDATION RESULTS")
    print("-" * 40)
    if checklist_result["audit"]["validations"]:
        print("Warnings/Errors found:")
        for val in checklist_result["audit"]["validations"][:5]:
            print(f"  - [{val['kind']}] {val['message']}")
    else:
        print("No validation issues found")
    
    print("\n" + "="*60)
    print("REPORT GENERATION COMPLETE")
    print("="*60)


def example_3_export_formats():
    """Example 3: Export reports in different formats"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Export Formats")
    print("="*60)
    
    # Create simple payload
    ui = UIInputs(
        contract_type="FFP",
        fiscal_years=["FY2025"],
        level="Total"
    )
    
    allocations = [
        Allocation(fy="FY2025", task="Direct Labor", cost=1000000),
        Allocation(fy="FY2025", task="Materials", cost=500000),
        Allocation(fy="FY2025", task="Overhead", cost=300000),
    ]
    
    payload = UnifiedPayload(ui=ui, allocations=allocations)
    
    # Generate in different formats
    print("\n1. JSON Format:")
    print("-" * 40)
    generate_body = GenerateBody(
        ui=ui,
        payload=payload,
        template="ANNUAL_FY",
        export_format="json"
    )
    json_result = generate(generate_body)
    print(json.dumps(json_result["metadata"], indent=2))
    
    print("\n2. Markdown Format (default):")
    print("-" * 40)
    generate_body.export_format = "markdown"
    # This returns a StreamingResponse, so we'd need to handle it differently in production
    print("Markdown export would download as .md file")
    
    print("\n3. CSV Format (allocations only):")
    print("-" * 40)
    generate_body.export_format = "csv"
    # This returns a StreamingResponse for CSV download
    print("CSV export would download allocations as .csv file")


def example_4_from_extraction():
    """Example 4: Generate reports from extraction service output"""
    print("\n" + "="*60)
    print("EXAMPLE 4: From Extraction Service")
    print("="*60)
    
    # Simulate extraction service response
    extraction_response = {
        "facts": [
            {
                "element": "Travel",
                "classification": "direct",
                "regulation": {"family": "FAR", "section": "31.205-46"},
                "citation_text": "Travel costs are allowable",
                "locator": {"document": "RFP", "page": 5},
                "confidence": 0.95
            },
            {
                "element": "Direct Labor",
                "classification": "direct",
                "regulation": {"family": "FAR", "section": "31.202"},
                "citation_text": "Direct labor includes engineering",
                "locator": {"document": "RFP", "page": 3},
                "confidence": 0.92
            }
        ],
        "metadata": {
            "total_raw": 2,
            "total_validated": 2,
            "extraction_timestamp": datetime.now().isoformat()
        }
    }
    
    ui = UIInputs(
        contract_type="CPFF",
        fiscal_years=["FY2025", "FY2026"]
    )
    
    # Generate DFARS checklist from extraction
    preview_body = PreviewBody(
        ui=ui,
        extraction_response=extraction_response,
        template="DFARS_CHECKLIST"
    )
    
    result = preview(preview_body)
    
    print("DFARS Checklist from Extraction:")
    print("-" * 40)
    for section in result["sections"]:
        print(section["content"][:800] + "...")  # Truncate for display
    
    print(f"\nExtraction had {len(extraction_response['facts'])} facts")
    print(f"Checklist shows compliance for extracted elements")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("ProposalOS RGE - Example Usage")
    print("="*60)
    print("\nThis script demonstrates how to use the Report Generation Engine")
    print("with DFARS templates and various data sources.\n")
    
    # Run examples
    try:
        # Try to use real KB file first
        example_1_basic_dfars_checklist()
    except Exception as e:
        print(f"Example 1 failed: {e}")
        # Fall back to synthetic data
        example_2_synthetic_data()
    
    try:
        example_3_export_formats()
    except Exception as e:
        print(f"Example 3 failed: {e}")
    
    try:
        example_4_from_extraction()
    except Exception as e:
        print(f"Example 4 failed: {e}")
    
    print("\n" + "="*60)
    print("All examples complete!")
    print("="*60)


if __name__ == "__main__":
    main()
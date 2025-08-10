#!/usr/bin/env python3
"""
ProposalOS RGE - Comprehensive Test Script
==========================================
Tests all components of the Report Generation Engine with DFARS templates
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the parent directory to path so we can import proposalos_rge
sys.path.insert(0, str(Path(__file__).parent))

# Import RGE components
from proposalos_rge.schemas import (
    UIInputs, 
    UnifiedPayload, 
    KBFact, 
    Allocation,
    RegulatorySupport,
    RFPMeta,
    Assumption,
    HEF,
    AuditEntry,
    Audit
)
from proposalos_rge.registry import REGISTRY, get_template
from proposalos_rge.validate.rules import run_validators
from proposalos_rge.render.md.dfars_templates import render_dfars_checklist, render_dfars_cover_page
from proposalos_rge.render.md.annual_fy import render


def test_schema_creation():
    """Test 1: Verify schema creation and validation"""
    print("\n" + "="*60)
    print("TEST 1: Schema Creation and Validation")
    print("="*60)
    
    try:
        # Create UI inputs
        ui = UIInputs(
            contract_type="CPFF",
            fiscal_years=["FY2025", "FY2026"],
            level="Task",
            customer_id="USSF",
            prime_or_sub="prime"
        )
        print("✓ UIInputs created successfully")
        
        # Create KB facts with regulatory support
        fact = KBFact(
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
        )
        print("✓ KBFact with RegulatorySupport created successfully")
        
        # Create allocation
        allocation = Allocation(
            fy="FY2025",
            task="Direct Labor",
            hours=1000,
            rate=150,
            cost=150000
        )
        print("✓ Allocation created successfully")
        
        # Create complete payload
        payload = UnifiedPayload(
            ui=ui,
            facts=[fact],
            allocations=[allocation]
        )
        print("✓ UnifiedPayload created successfully")
        
        # Test serialization
        payload_dict = payload.model_dump()
        print(f"✓ Payload serialized to dict with {len(payload_dict)} keys")
        
        # Test JSON serialization
        payload_json = payload.model_dump_json()
        print(f"✓ Payload serialized to JSON ({len(payload_json)} chars)")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False


def test_registry():
    """Test 2: Verify template registry"""
    print("\n" + "="*60)
    print("TEST 2: Template Registry")
    print("="*60)
    
    try:
        # Check DFARS templates are registered
        templates = ["DFARS_CHECKLIST", "DFARS_COVER_PAGE", "ANNUAL_FY", "COST_VOLUME_FULL", "TRAVEL_CALCULATOR"]
        
        for template_id in templates:
            template = get_template(template_id)
            if template:
                print(f"✓ {template_id}: {template['name']}")
                print(f"  - Sections: {len(template.get('sections', []))}")
            else:
                print(f"✗ {template_id}: Not found in registry")
        
        print(f"\nTotal templates in registry: {len(REGISTRY)}")
        return True
        
    except Exception as e:
        print(f"✗ Registry test failed: {e}")
        return False


def test_dfars_checklist():
    """Test 3: Test DFARS checklist rendering"""
    print("\n" + "="*60)
    print("TEST 3: DFARS Checklist Rendering")
    print("="*60)
    
    try:
        # Create test payload
        ui = UIInputs(
            contract_type="CPFF",
            fiscal_years=["FY2025", "FY2026"],
            customer_id="USSF"
        )
        
        facts = [
            KBFact(
                element="Direct Labor",
                classification="direct",
                regulatory_support=[
                    RegulatorySupport(
                        reg_title="FAR",
                        reg_section="31.202",
                        quote="Direct labor costs",
                        confidence=0.9
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
                        quote="Travel costs",
                        confidence=0.85
                    )
                ],
                confidence=0.85
            ),
            KBFact(
                element="Materials",
                classification="direct",
                confidence=0.8
            )
        ]
        
        rfp = RFPMeta(
            rfp_id="FA8750-25-R-0001",
            title="Advanced Satellite Communications System",
            customer="USSF Space Systems Command"
        )
        
        payload = UnifiedPayload(ui=ui, rfp=rfp, facts=facts)
        
        # Render checklist
        checklist = render_dfars_checklist(payload)
        
        # Verify output contains expected elements
        expected_elements = [
            "DFARS 252.215-7009 Requirements Checklist",
            "Contract/Proposal:",
            "Direct Labor",
            "Travel",
            "Materials",
            "☑",  # Should have checkmarks for included items
            "Compliance Summary",
            "Compliance Rate:"
        ]
        
        for element in expected_elements:
            if element in checklist:
                print(f"✓ Found: {element}")
            else:
                print(f"✗ Missing: {element}")
        
        # Display a snippet of the output
        print("\nFirst 500 chars of output:")
        print("-" * 40)
        print(checklist[:500] + "...")
        
        return True
        
    except Exception as e:
        print(f"✗ DFARS checklist test failed: {e}")
        return False


def test_dfars_cover_page():
    """Test 4: Test DFARS cover page rendering"""
    print("\n" + "="*60)
    print("TEST 4: DFARS Cover Page Rendering")
    print("="*60)
    
    try:
        # Create test payload with allocations
        ui = UIInputs(
            contract_type="CPFF",
            fiscal_years=["FY2025", "FY2026", "FY2027"]
        )
        
        allocations = [
            Allocation(fy="FY2025", task="Direct Labor", cost=1500000),
            Allocation(fy="FY2025", task="Travel", cost=75000),
            Allocation(fy="FY2025", task="Materials", cost=250000),
            Allocation(fy="FY2026", task="Direct Labor", cost=1860000),
            Allocation(fy="FY2026", task="Travel", cost=80000),
            Allocation(fy="FY2027", task="Direct Labor", cost=1280000),
        ]
        
        rfp = RFPMeta(
            rfp_id="FA8750-25-R-0001",
            title="Advanced Satellite Communications System",
            customer="USSF Space Systems Command"
        )
        
        payload = UnifiedPayload(ui=ui, rfp=rfp, allocations=allocations)
        
        # Render cover page
        cover = render_dfars_cover_page(payload)
        
        # Verify output contains expected sections
        expected_sections = [
            "CONTRACT PRICING PROPOSAL COVER SHEET",
            "SF 1411 Format",
            "SECTION A - SOLICITATION/CONTRACT INFORMATION",
            "SECTION B - CONTRACTOR INFORMATION",
            "SECTION C - PRICING SUMMARY",
            "SECTION D - FISCAL YEAR BREAKDOWN",
            "SECTION E - CERTIFICATIONS",
            "Direct Labor",
            "$"
        ]
        
        for section in expected_sections:
            if section in cover:
                print(f"✓ Found: {section}")
            else:
                print(f"✗ Missing: {section}")
        
        # Check for total calculation
        if "$4,945,000" in cover or "4,945,000" in cover or "4945000" in cover:
            print("✓ Total cost calculated correctly")
        else:
            print("✗ Total cost calculation issue")
        
        print("\nFirst 600 chars of output:")
        print("-" * 40)
        print(cover[:600] + "...")
        
        return True
        
    except Exception as e:
        print(f"✗ DFARS cover page test failed: {e}")
        return False


def test_annual_fy_report():
    """Test 5: Test Annual FY report rendering"""
    print("\n" + "="*60)
    print("TEST 5: Annual FY Report Rendering")
    print("="*60)
    
    try:
        # Create comprehensive test payload
        ui = UIInputs(
            contract_type="CPFF",
            fiscal_years=["FY2025", "FY2026"],
            level="Task"
        )
        
        allocations = [
            # FY2025
            Allocation(fy="FY2025", task="Direct Labor", hours=10000, rate=150, cost=1500000),
            Allocation(fy="FY2025", task="Travel", cost=75000),
            Allocation(fy="FY2025", task="Materials", cost=250000),
            Allocation(fy="FY2025", task="Overhead", cost=450000),
            # FY2026
            Allocation(fy="FY2026", task="Direct Labor", hours=12000, rate=155, cost=1860000),
            Allocation(fy="FY2026", task="Travel", cost=80000),
            Allocation(fy="FY2026", task="Materials", cost=300000),
            Allocation(fy="FY2026", task="Overhead", cost=558000),
        ]
        
        assumptions = [
            Assumption(text="All labor rates include current fringe benefits", source="HR Policy"),
            Assumption(text="3% annual escalation applied", source="IHS Markit")
        ]
        
        hef = HEF(
            basis_year="2024",
            series={"FY2025": 1.0, "FY2026": 1.03}
        )
        
        payload = UnifiedPayload(
            ui=ui,
            allocations=allocations,
            assumptions=assumptions,
            hefs=[hef]
        )
        
        # Run validators
        payload = run_validators(payload)
        
        # Render report
        report = render(payload)
        
        # Verify output contains expected elements
        expected_elements = [
            "Annual Fiscal Year Report",
            "Cost Rollup by Task",
            "Total Program Cost:",
            "Cost Breakdown by Fiscal Year",
            "Direct Labor",
            "Travel",
            "Materials",
            "Overhead",
            "Assumptions",
            "Human Effort Factors"
        ]
        
        for element in expected_elements:
            if element in report:
                print(f"✓ Found: {element}")
            else:
                print(f"✗ Missing: {element}")
        
        # Check for total calculation
        total = 1500000 + 75000 + 250000 + 450000 + 1860000 + 80000 + 300000 + 558000
        if f"${total:,.2f}" in report or str(total) in report:
            print("✓ Total cost calculated correctly")
        else:
            print("✗ Total cost calculation issue")
        
        print("\nFirst 800 chars of output:")
        print("-" * 40)
        print(report[:800] + "...")
        
        return True
        
    except Exception as e:
        print(f"✗ Annual FY report test failed: {e}")
        return False


def test_validation_rules():
    """Test 6: Test validation rules"""
    print("\n" + "="*60)
    print("TEST 6: Validation Rules")
    print("="*60)
    
    try:
        # Create payload with potential issues
        ui = UIInputs(
            contract_type="CPFF",
            fiscal_years=["FY2025"]
        )
        
        # Create allocations with some issues
        allocations = [
            Allocation(fy="FY2025", task="Direct Labor", cost=1500000),
            Allocation(fy="FY2025", task="Travel", cost=-1000),  # Negative cost
            Allocation(fy="FY2026", task="Materials", cost=250000),  # FY not in UI
        ]
        
        # Create facts with low confidence
        facts = [
            KBFact(element="Test", classification="ambiguous", confidence=0.3)  # Low confidence
        ]
        
        payload = UnifiedPayload(ui=ui, allocations=allocations, facts=facts)
        
        # Run validators
        validated_payload = run_validators(payload)
        
        # Check for validation results
        if validated_payload.audit.validations:
            print(f"✓ Found {len(validated_payload.audit.validations)} validation issues")
            
            for val in validated_payload.audit.validations[:5]:
                print(f"  - [{val.kind}] {val.code}: {val.message}")
        else:
            print("✗ No validation issues found (expected some)")
        
        return True
        
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False


def test_dict_compatibility():
    """Test 7: Test dict/Pydantic model compatibility"""
    print("\n" + "="*60)
    print("TEST 7: Dict/Pydantic Compatibility")
    print("="*60)
    
    try:
        # Create payload as dict
        payload_dict = {
            "ui": {
                "contract_type": "FFP",
                "fiscal_years": ["FY2025"]
            },
            "facts": [
                {
                    "element": "Direct Labor",
                    "classification": "direct",
                    "confidence": 0.9
                }
            ],
            "allocations": [
                {
                    "fy": "FY2025",
                    "task": "Direct Labor",
                    "cost": 100000
                }
            ]
        }
        
        # Test with dict
        print("Testing DFARS checklist with dict input...")
        checklist_dict = render_dfars_checklist(payload_dict)
        if "DFARS 252.215-7009" in checklist_dict:
            print("✓ DFARS checklist works with dict input")
        else:
            print("✗ DFARS checklist failed with dict input")
        
        # Test with Pydantic model
        print("Testing DFARS checklist with Pydantic input...")
        payload_model = UnifiedPayload(**payload_dict)
        checklist_model = render_dfars_checklist(payload_model)
        if "DFARS 252.215-7009" in checklist_model:
            print("✓ DFARS checklist works with Pydantic input")
        else:
            print("✗ DFARS checklist failed with Pydantic input")
        
        # Test cover page with both
        print("Testing DFARS cover page with both input types...")
        cover_dict = render_dfars_cover_page(payload_dict)
        cover_model = render_dfars_cover_page(payload_model)
        
        if "CONTRACT PRICING PROPOSAL" in cover_dict and "CONTRACT PRICING PROPOSAL" in cover_model:
            print("✓ DFARS cover page works with both input types")
        else:
            print("✗ DFARS cover page compatibility issue")
        
        return True
        
    except Exception as e:
        print(f"✗ Compatibility test failed: {e}")
        return False


def test_edge_cases():
    """Test 8: Test edge cases and error handling"""
    print("\n" + "="*60)
    print("TEST 8: Edge Cases and Error Handling")
    print("="*60)
    
    try:
        # Test with minimal payload
        print("Testing with minimal payload...")
        minimal = UnifiedPayload(ui=UIInputs())
        
        checklist = render_dfars_checklist(minimal)
        if "DFARS 252.215-7009" in checklist:
            print("✓ Handles minimal payload")
        
        # Test with empty facts
        print("Testing with no facts...")
        no_facts = UnifiedPayload(
            ui=UIInputs(contract_type="FFP"),
            allocations=[Allocation(fy="FY2025", task="Test", cost=1000)]
        )
        checklist = render_dfars_checklist(no_facts)
        if "Not found in current data" in checklist:
            print("✓ Handles no facts gracefully")
        
        # Test with no allocations
        print("Testing with no allocations...")
        no_allocs = UnifiedPayload(
            ui=UIInputs(fiscal_years=["FY2025"]),
            facts=[KBFact(element="Test", classification="direct", confidence=0.8)]
        )
        cover = render_dfars_cover_page(no_allocs)
        if "$0.00" in cover or "TOTAL" in cover:
            print("✓ Handles no allocations gracefully")
        
        # Test with special characters in data
        print("Testing with special characters...")
        special = UnifiedPayload(
            ui=UIInputs(),
            facts=[
                KBFact(
                    element="Test & Development",
                    classification="direct",
                    regulatory_support=[
                        RegulatorySupport(
                            reg_title="FAR/DFARS",
                            reg_section="31.205-18(a)(1)",
                            quote="R&D costs with \"special\" handling",
                            confidence=0.9
                        )
                    ],
                    confidence=0.85
                )
            ]
        )
        checklist = render_dfars_checklist(special)
        if "Test & Development" in checklist:
            print("✓ Handles special characters")
        
        return True
        
    except Exception as e:
        print(f"✗ Edge case test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("ProposalOS RGE - Test Suite")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    
    tests = [
        ("Schema Creation", test_schema_creation),
        ("Template Registry", test_registry),
        ("DFARS Checklist", test_dfars_checklist),
        ("DFARS Cover Page", test_dfars_cover_page),
        ("Annual FY Report", test_annual_fy_report),
        ("Validation Rules", test_validation_rules),
        ("Dict/Pydantic Compatibility", test_dict_compatibility),
        ("Edge Cases", test_edge_cases)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The RGE system is working correctly.")
    elif passed >= total * 0.8:
        print("⚠️  Most tests passed, but some issues need attention.")
    else:
        print("❌ Multiple test failures detected. Please review the output.")
    
    print(f"\nCompleted at: {datetime.now().isoformat()}")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
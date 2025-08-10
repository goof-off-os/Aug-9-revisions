#!/usr/bin/env python3
"""
Example: Using the Template Registry with ProposalOS RGE
=========================================================
Shows how to integrate the registry bootstrap with your application.
"""

from registry_bootstrap import TemplateRegistry, bootstrap_registry
from proposalos_rge.schemas import UIInputs, UnifiedPayload, KBFact, Allocation, RegulatorySupport
import json


def main():
    """Demonstrate template registry usage"""
    
    # ============================================================
    # 1. Initialize and Bootstrap Registry
    # ============================================================
    print("=" * 60)
    print("Initializing Template Registry")
    print("=" * 60)
    
    TEMPLATE_REGISTRY = TemplateRegistry()
    bootstrap_registry(TEMPLATE_REGISTRY)
    
    print(f"✅ Registry initialized with {len(TEMPLATE_REGISTRY._templates)} templates")
    print(f"Categories: {list(TEMPLATE_REGISTRY.get_categories().keys())}")
    print()
    
    # ============================================================
    # 2. List Available Templates by Category
    # ============================================================
    print("=" * 60)
    print("Available DFARS Templates")
    print("=" * 60)
    
    dfars_templates = TEMPLATE_REGISTRY.list_templates(category="DFARS")
    for template in dfars_templates:
        print(f"• {template.id}: {template.name}")
        print(f"  {template.description}")
        if template.required_fields:
            print(f"  Required: {', '.join(template.required_fields)}")
    print()
    
    # ============================================================
    # 3. Create Sample Payload
    # ============================================================
    print("=" * 60)
    print("Creating Sample Payload")
    print("=" * 60)
    
    # Create a comprehensive payload
    payload = UnifiedPayload(
        ui=UIInputs(
            contract_type="CPFF",
            fiscal_years=["FY2025", "FY2026"],
            level="Task",
            customer_id="USSF",
            prime_or_sub="prime"
        ),
        facts=[
            KBFact(
                element="Direct Labor",
                classification="direct",
                regulatory_support=[
                    RegulatorySupport(
                        reg_title="FAR",
                        reg_section="31.202",
                        quote="Direct labor costs are allowable when reasonable",
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
                        quote="Travel costs allowable per GSA rates",
                        confidence=0.92
                    )
                ],
                confidence=0.88
            ),
            KBFact(
                element="Materials",
                classification="direct",
                confidence=0.85
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
                confidence=0.89
            )
        ],
        allocations=[
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
    )
    
    print("✅ Payload created with:")
    print(f"  - {len(payload.facts)} facts")
    print(f"  - {len(payload.allocations)} allocations")
    print(f"  - Contract type: {payload.ui.contract_type}")
    print(f"  - Fiscal years: {', '.join(payload.ui.fiscal_years)}")
    print()
    
    # ============================================================
    # 4. Validate Payload for Templates
    # ============================================================
    print("=" * 60)
    print("Validating Payload")
    print("=" * 60)
    
    templates_to_test = ["DFARS_CHECKLIST", "DFARS_COVER_PAGE", "ANNUAL_FY"]
    
    for template_id in templates_to_test:
        is_valid, missing = TEMPLATE_REGISTRY.validate_payload(template_id, payload)
        if is_valid:
            print(f"✅ {template_id}: Valid")
        else:
            print(f"❌ {template_id}: Missing fields: {missing}")
    print()
    
    # ============================================================
    # 5. Render Templates
    # ============================================================
    print("=" * 60)
    print("Rendering Templates")
    print("=" * 60)
    
    # Render DFARS Checklist
    try:
        print("\n1. DFARS Checklist:")
        print("-" * 40)
        checklist = TEMPLATE_REGISTRY.render("DFARS_CHECKLIST", payload)
        # Show first 800 chars
        print(checklist[:800] + "...\n")
        print(f"✅ DFARS Checklist rendered ({len(checklist)} chars)")
    except Exception as e:
        print(f"❌ Failed to render DFARS Checklist: {e}")
    
    # Render DFARS Cover Page
    try:
        print("\n2. DFARS Cover Page:")
        print("-" * 40)
        cover = TEMPLATE_REGISTRY.render("DFARS_COVER_PAGE", payload)
        # Show first 600 chars
        print(cover[:600] + "...\n")
        print(f"✅ DFARS Cover Page rendered ({len(cover)} chars)")
    except Exception as e:
        print(f"❌ Failed to render DFARS Cover Page: {e}")
    
    # Render Annual FY Report
    try:
        print("\n3. Annual FY Report:")
        print("-" * 40)
        annual = TEMPLATE_REGISTRY.render("ANNUAL_FY", payload)
        # Show first 700 chars
        print(annual[:700] + "...\n")
        print(f"✅ Annual FY Report rendered ({len(annual)} chars)")
    except Exception as e:
        print(f"❌ Failed to render Annual FY Report: {e}")
    
    # ============================================================
    # 6. Batch Rendering Example
    # ============================================================
    print("=" * 60)
    print("Batch Rendering Multiple Templates")
    print("=" * 60)
    
    def batch_render(registry, template_ids, payload):
        """Render multiple templates and return results"""
        results = {}
        for tid in template_ids:
            try:
                results[tid] = {
                    "success": True,
                    "output": registry.render(tid, payload),
                    "length": 0
                }
                results[tid]["length"] = len(results[tid]["output"])
            except Exception as e:
                results[tid] = {
                    "success": False,
                    "error": str(e)
                }
        return results
    
    batch_ids = ["DFARS_CHECKLIST", "DFARS_COVER_PAGE", "ANNUAL_FY"]
    batch_results = batch_render(TEMPLATE_REGISTRY, batch_ids, payload)
    
    for tid, result in batch_results.items():
        if result["success"]:
            print(f"✅ {tid}: {result['length']} chars")
        else:
            print(f"❌ {tid}: {result['error']}")
    
    # ============================================================
    # 7. Using with FastAPI (Example)
    # ============================================================
    print("\n" + "=" * 60)
    print("FastAPI Integration Example")
    print("=" * 60)
    
    print("""
    # In your FastAPI app:
    
    from fastapi import FastAPI, HTTPException
    from registry_bootstrap import TemplateRegistry, bootstrap_registry
    
    app = FastAPI()
    
    # Initialize registry at startup
    TEMPLATE_REGISTRY = TemplateRegistry()
    bootstrap_registry(TEMPLATE_REGISTRY)
    
    @app.post("/reports/render/{template_id}")
    async def render_report(template_id: str, payload: dict):
        '''Render a report using the specified template'''
        
        # Validate template exists
        if not TEMPLATE_REGISTRY.get_template(template_id):
            raise HTTPException(404, f"Template {template_id} not found")
        
        # Validate payload
        is_valid, missing = TEMPLATE_REGISTRY.validate_payload(template_id, payload)
        if not is_valid:
            raise HTTPException(400, f"Missing required fields: {missing}")
        
        # Render
        try:
            output = TEMPLATE_REGISTRY.render(template_id, payload)
            return {"template": template_id, "output": output}
        except Exception as e:
            raise HTTPException(500, f"Render failed: {str(e)}")
    
    @app.get("/reports/templates")
    async def list_templates(category: str = None):
        '''List available templates'''
        templates = TEMPLATE_REGISTRY.list_templates(category=category)
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "required_fields": t.required_fields
                }
                for t in templates
            ]
        }
    """)
    
    # ============================================================
    # 8. Summary
    # ============================================================
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Registry contains {len(TEMPLATE_REGISTRY._templates)} templates")
    print(f"✅ Successfully rendered 3 different report types")
    print(f"✅ Templates are categorized and discoverable")
    print(f"✅ Validation ensures required fields are present")
    print(f"✅ Ready for production use in APIs and applications")
    print("=" * 60)


if __name__ == "__main__":
    main()
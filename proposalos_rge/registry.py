# proposalos_rge/registry.py
from typing import Dict, List, TypedDict, Optional

class SectionSpec(TypedDict, total=False):
    id: str
    renderer: str  # dotted path, e.g., "proposalos_rge.render.md.annual_fy:render"
    title: str
    required_fields: List[str]

class TemplateSpec(TypedDict, total=False):
    name: str
    description: str
    sections: List[SectionSpec]

REGISTRY: Dict[str, TemplateSpec] = {
    "ANNUAL_FY": {
        "name": "Annual Fiscal Year Rollup",
        "description": "Per-FY cost rollups at selected level.",
        "sections": [
            {
                "id": "annual_fy_core",
                "title": "Annual FY Rollup",
                "renderer": "proposalos_rge.render.md.annual_fy:render",
                "required_fields": ["allocations"]
            }
        ]
    },
    "DFARS_CHECKLIST": {
        "name": "DFARS 252.215-7009 Requirements Checklist",
        "description": "Compliance checklist for certified cost or pricing data",
        "category": "DFARS",
        "format": "text/markdown",
        "sections": [
            {
                "id": "dfars_checklist",
                "title": "DFARS Compliance Checklist",
                "renderer": "proposalos_rge.render.md.dfars_templates:render_dfars_checklist",
                "required_fields": ["facts"]
            }
        ]
    },
    "DFARS_COVER_PAGE": {
        "name": "DFARS Cover Page (SF1411-style)",
        "description": "Contract pricing proposal cover sheet",
        "category": "DFARS",
        "format": "text/markdown",
        "sections": [
            {
                "id": "dfars_cover",
                "title": "Contract Pricing Proposal Cover Sheet",
                "renderer": "proposalos_rge.render.md.dfars_templates:render_dfars_cover_page",
                "required_fields": ["allocations"]
            }
        ]
    },
    "COST_VOLUME_FULL": {
        "name": "Complete Cost Volume",
        "description": "Full cost volume with all sections.",
        "sections": [
            {
                "id": "executive_summary",
                "title": "Executive Summary",
                "renderer": "proposalos_rge.render.md.cost_volume:render_executive_summary",
                "required_fields": ["facts", "allocations"]
            },
            {
                "id": "cost_buildup",
                "title": "Cost Buildup",
                "renderer": "proposalos_rge.render.md.cost_volume:render_cost_buildup",
                "required_fields": ["allocations"]
            },
            {
                "id": "regulatory_compliance",
                "title": "Regulatory Compliance",
                "renderer": "proposalos_rge.render.md.cost_volume:render_compliance",
                "required_fields": ["facts"]
            }
        ]
    },
    "TRAVEL_CALCULATOR": {
        "name": "Travel Cost Summary",
        "description": "Travel cost calculations with GSA rates.",
        "sections": [
            {
                "id": "travel_summary",
                "title": "Travel Cost Summary",
                "renderer": "proposalos_rge.render.md.travel:render_summary",
                "required_fields": ["allocations"]
            }
        ]
    }
}

def get_template(template_id: str) -> Optional[TemplateSpec]:
    """Get template specification by ID"""
    return REGISTRY.get(template_id)
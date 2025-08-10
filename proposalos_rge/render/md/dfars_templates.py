# proposalos_rge/render/md/dfars_templates.py
"""
DFARS Report Templates
======================
Provides DFARS 252.215-7009 Checklist and SF1411-style Cover Page renderers
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from ...schemas import UnifiedPayload, KBFact


# DFARS 252.215-7009 Checklist items (starter set - extendable)
_CHECKLIST_ROWS = [
    {
        "item": "1",
        "description": "Direct Labor (Engineering, Manufacturing, etc.)",
        "element": "Direct Labor",
        "regulation": "FAR 31.202",
        "provided": "☐",
        "remarks": ""
    },
    {
        "item": "2",
        "description": "Travel Costs",
        "element": "Travel",
        "regulation": "FAR 31.205-46",
        "provided": "☐",
        "remarks": ""
    },
    {
        "item": "3",
        "description": "Direct Materials",
        "element": "Materials",
        "regulation": "FAR 31.205-26",
        "provided": "☐",
        "remarks": ""
    },
    {
        "item": "4",
        "description": "Subcontracts",
        "element": "Subcontracts",
        "regulation": "FAR Part 44",
        "provided": "☐",
        "remarks": ""
    },
    {
        "item": "5",
        "description": "Other Direct Costs (ODCs)",
        "element": "ODC",
        "regulation": "FAR 31.205",
        "provided": "☐",
        "remarks": ""
    },
    {
        "item": "6",
        "description": "Indirect Costs (Overhead, G&A, Fringe)",
        "element": "Overhead",
        "regulation": "FAR 31.203",
        "provided": "☐",
        "remarks": ""
    }
]


def render_dfars_checklist(
    payload: UnifiedPayload,
    kb: Optional[Dict[str, Any]] = None
) -> str:
    """
    Render DFARS 252.215-7009 Requirements Checklist
    
    Args:
        payload: Unified payload (dict or Pydantic model)
        kb: Optional knowledge base for additional context
        
    Returns:
        Markdown formatted checklist
    """
    # Handle both dict and Pydantic model
    if hasattr(payload, 'dict'):
        payload_dict = payload.dict()
    else:
        payload_dict = payload if isinstance(payload, dict) else {}
    
    # Extract facts
    facts = payload_dict.get('facts', []) if isinstance(payload_dict, dict) else payload.facts
    
    # Build element set from facts
    element_set = set()
    element_regulations = {}
    
    for fact in facts:
        if isinstance(fact, dict):
            element = fact.get('element', '')
            element_set.add(element)
            # Track regulations for each element
            if 'regulatory_support' in fact:
                for reg in fact.get('regulatory_support', []):
                    if element not in element_regulations:
                        element_regulations[element] = []
                    element_regulations[element].append(
                        f"{reg.get('reg_title', '')} {reg.get('reg_section', '')}"
                    )
        else:
            element = fact.element
            element_set.add(element)
            for reg in fact.regulatory_support:
                if element not in element_regulations:
                    element_regulations[element] = []
                element_regulations[element].append(f"{reg.reg_title} {reg.reg_section}")
    
    # Build the checklist
    lines = [
        "# DFARS 252.215-7009 Requirements Checklist",
        "",
        "**Contract/Proposal:** " + _safe_get(payload_dict, 'rfp.title', 'TBD'),
        "**Date:** " + datetime.utcnow().strftime("%Y-%m-%d"),
        "**Prepared By:** " + _safe_get(payload_dict, 'ui.customer_id', 'ProposalOS'),
        "",
        "## Certified Cost or Pricing Data Requirements",
        "",
        "| Item | Description | FAR/DFARS Reference | Provided | Remarks |",
        "|------|-------------|---------------------|----------|---------|"
    ]
    
    # Process each checklist row
    for row in _CHECKLIST_ROWS:
        element = row['element']
        
        # Check if element is present in facts
        if element in element_set:
            provided = "☑"
            # Add regulations found in facts
            regulations = element_regulations.get(element, [row['regulation']])
            regulation_text = ', '.join(set(regulations)) if regulations else row['regulation']
            remarks = "Mapped from KB/Facts"
        else:
            provided = "☐"
            regulation_text = row['regulation']
            remarks = "Not found in current data"
        
        lines.append(
            f"| {row['item']} | {row['description']} | {regulation_text} | {provided} | {remarks} |"
        )
    
    # Add additional elements found in facts but not in checklist
    item_num = len(_CHECKLIST_ROWS) + 1
    for element in element_set:
        if element not in [r['element'] for r in _CHECKLIST_ROWS]:
            regulations = element_regulations.get(element, ['TBD'])
            lines.append(
                f"| {item_num} | {element} | {', '.join(regulations)} | ☑ | Additional element from facts |"
            )
            item_num += 1
    
    # Add notes section
    lines.extend([
        "",
        "## Notes",
        "",
        "- ☑ = Data provided/mapped from knowledge base",
        "- ☐ = Data not yet provided",
        "- This checklist addresses the requirements of DFARS 252.215-7009",
        "- Additional supporting documentation may be required",
        "",
        "## Compliance Summary",
        ""
    ])
    
    # Calculate compliance percentage
    total_items = len(_CHECKLIST_ROWS)
    provided_items = len([e for e in [r['element'] for r in _CHECKLIST_ROWS] if e in element_set])
    compliance_pct = (provided_items / total_items * 100) if total_items > 0 else 0
    
    lines.extend([
        f"- **Total Requirements:** {total_items}",
        f"- **Requirements Met:** {provided_items}",
        f"- **Compliance Rate:** {compliance_pct:.1f}%",
        f"- **Additional Elements:** {len(element_set - set(r['element'] for r in _CHECKLIST_ROWS))}"
    ])
    
    # Add validation warnings if present
    if hasattr(payload, 'audit') or 'audit' in payload_dict:
        audit = payload.audit if hasattr(payload, 'audit') else payload_dict.get('audit', {})
        if audit:
            validations = audit.get('validations', []) if isinstance(audit, dict) else audit.validations
            if validations:
                lines.extend([
                    "",
                    "## Validation Issues",
                    ""
                ])
                for val in validations[:5]:  # Limit to first 5
                    kind = val.get('kind', 'info') if isinstance(val, dict) else val.kind
                    message = val.get('message', '') if isinstance(val, dict) else val.message
                    lines.append(f"- [{kind.upper()}] {message}")
    
    lines.extend([
        "",
        "---",
        "*Generated by ProposalOS RGE - DFARS Checklist Module*"
    ])
    
    return "\n".join(lines)


def render_dfars_cover_page(
    payload: UnifiedPayload,
    kb: Optional[Dict[str, Any]] = None
) -> str:
    """
    Render SF1411-style DFARS Cover Page
    
    Args:
        payload: Unified payload (dict or Pydantic model)
        kb: Optional knowledge base for additional context
        
    Returns:
        Markdown formatted cover page
    """
    # Handle both dict and Pydantic model
    if hasattr(payload, 'dict'):
        payload_dict = payload.dict()
    else:
        payload_dict = payload if isinstance(payload, dict) else {}
    
    # Extract key information
    rfp = payload_dict.get('rfp', {}) if isinstance(payload_dict, dict) else getattr(payload, 'rfp', None)
    ui = payload_dict.get('ui', {}) if isinstance(payload_dict, dict) else getattr(payload, 'ui', None)
    
    lines = [
        "# CONTRACT PRICING PROPOSAL COVER SHEET",
        "## (SF 1411 Format - DFARS Compliant)",
        "",
        "---",
        "",
        "### SECTION A - SOLICITATION/CONTRACT INFORMATION",
        "",
        "**1. SOLICITATION NUMBER:** " + _safe_get(rfp, 'rfp_id', 'TBD'),
        "**2. PROPOSAL TITLE:** " + _safe_get(rfp, 'title', 'TBD'),
        "**3. CUSTOMER/AGENCY:** " + _safe_get(rfp, 'customer', 'TBD'),
        "**4. CONTRACT TYPE:** " + _safe_get(ui, 'contract_type', 'TBD'),
        "**5. PROPOSAL DATE:** " + datetime.utcnow().strftime("%Y-%m-%d"),
        "",
        "### SECTION B - CONTRACTOR INFORMATION",
        "",
        "**6. CONTRACTOR NAME:** [CONTRACTOR NAME]",
        "**7. CAGE CODE:** [CAGE CODE]",
        "**8. DUNS NUMBER:** [DUNS NUMBER]",
        "**9. TIN:** [TIN]",
        "**10. FACILITY CLEARANCE:** [CLEARANCE LEVEL]",
        "",
        "### SECTION C - PRICING SUMMARY",
        ""
    ]
    
    # Calculate totals from allocations if available
    allocations = payload_dict.get('allocations', []) if isinstance(payload_dict, dict) else getattr(payload, 'allocations', [])
    
    total_cost = 0
    fy_totals = {}
    
    for alloc in allocations:
        if isinstance(alloc, dict):
            cost = alloc.get('cost', 0)
            fy = alloc.get('fy', 'Unknown')
        else:
            cost = alloc.cost or 0
            fy = alloc.fy
        
        total_cost += cost
        fy_totals[fy] = fy_totals.get(fy, 0) + cost
    
    lines.append("| Element | Amount | % of Total |")
    lines.append("|---------|--------|------------|")
    
    # Group allocations by task/element
    element_totals = {}
    for alloc in allocations:
        if isinstance(alloc, dict):
            element = alloc.get('task', 'Other')
            cost = alloc.get('cost', 0)
        else:
            element = alloc.task or 'Other'
            cost = alloc.cost or 0
        
        element_totals[element] = element_totals.get(element, 0) + cost
    
    # Standard cost elements
    standard_elements = ['Direct Labor', 'Travel', 'Materials', 'Subcontracts', 'ODC', 'Overhead', 'G&A', 'Fee/Profit']
    
    for element in standard_elements:
        amount = element_totals.get(element, 0)
        pct = (amount / total_cost * 100) if total_cost > 0 else 0
        if amount > 0:
            lines.append(f"| {element} | ${amount:,.2f} | {pct:.1f}% |")
        else:
            lines.append(f"| {element} | $0.00 | 0.0% |")
    
    # Add other elements
    for element, amount in element_totals.items():
        if element not in standard_elements and amount > 0:
            pct = (amount / total_cost * 100) if total_cost > 0 else 0
            lines.append(f"| {element} | ${amount:,.2f} | {pct:.1f}% |")
    
    lines.append(f"| **TOTAL** | **${total_cost:,.2f}** | **100.0%** |")
    
    # Add fiscal year breakdown
    if fy_totals:
        lines.extend([
            "",
            "### SECTION D - FISCAL YEAR BREAKDOWN",
            "",
            "| Fiscal Year | Amount |",
            "|-------------|--------|"
        ])
        
        for fy in sorted(fy_totals.keys()):
            lines.append(f"| {fy} | ${fy_totals[fy]:,.2f} |")
    
    # Add certifications section
    lines.extend([
        "",
        "### SECTION E - CERTIFICATIONS",
        "",
        "**11. COST OR PRICING DATA (FAR 15.403-4):**",
        "- [ ] Certified cost or pricing data were submitted",
        "- [ ] Certified cost or pricing data were not submitted",
        "- [ ] Exception claimed under FAR 15.403-1(b)",
        "",
        "**12. DCAA AUDIT:**",
        "- [ ] DCAA audit completed",
        "- [ ] DCAA audit pending",
        "- [ ] DCAA audit not required",
        "",
        "**13. SMALL BUSINESS SUBCONTRACTING PLAN:**",
        "- [ ] Required and submitted",
        "- [ ] Not required",
        "",
        "### SECTION F - SIGNATURES",
        "",
        "**CONTRACTOR:**",
        "Signature: _________________________  Date: __________",
        "Name: [NAME]",
        "Title: [TITLE]",
        "",
        "**CONTRACTING OFFICER:**",
        "Signature: _________________________  Date: __________",
        "Name: [NAME]",
        "Title: Contracting Officer",
        "",
        "---",
        "",
        "### ATTACHMENTS",
        "",
        "The following documents are attached and made part of this proposal:",
        "",
        "- [ ] Cost Element Breakdown (Section L Requirements)",
        "- [ ] Technical Proposal",
        "- [ ] Past Performance Information",
        "- [ ] Subcontracting Plan",
        "- [ ] DCAA Forward Pricing Rate Agreement (if applicable)",
        "- [ ] Other: _________________________",
        "",
        "---",
        "*This cover sheet complies with DFARS 252.215-7009 requirements*",
        "*Generated by ProposalOS RGE - DFARS Cover Page Module*"
    ])
    
    return "\n".join(lines)


def _safe_get(obj: Any, path: str, default: str = "TBD") -> str:
    """
    Safely get a value from an object/dict with dot notation
    
    Args:
        obj: Object or dict to get value from
        path: Dot-separated path (e.g., 'rfp.title')
        default: Default value if not found
        
    Returns:
        Value at path or default
    """
    if obj is None:
        return default
    
    parts = path.split('.')
    current = obj
    
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return default
        
        if current is None:
            return default
    
    return str(current) if current is not None else default


def register(registry: Dict[str, Dict]) -> None:
    """
    Register DFARS templates in the provided registry
    
    Args:
        registry: Template registry dictionary to update
    """
    # Register DFARS Checklist
    if "DFARS_CHECKLIST" not in registry:
        registry["DFARS_CHECKLIST"] = {
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
        }
    
    # Register DFARS Cover Page
    if "DFARS_COVER_PAGE" not in registry:
        registry["DFARS_COVER_PAGE"] = {
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
        }
    
    return registry
# proposalos_rge/render/md/annual_fy.py
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any
from ...schemas import UnifiedPayload, Allocation


def _infer_allocations_from_facts(payload: UnifiedPayload) -> List[Allocation]:
    """
    MVP shim: if caller didn't provide allocations, create a toy rollup
    by counting fact elements per FY (placeholder logic).
    Replace with your real CLIN/WBS rollup once available.
    
    Args:
        payload: Unified payload
        
    Returns:
        List of inferred allocations
    """
    if payload.allocations:
        return payload.allocations

    # Naive placeholder: one $1,000 per fact to FY of ui.fiscal_years[0]
    fy = (payload.ui.fiscal_years or ["FY2025"])[0]
    allocs = []
    
    for fact in payload.facts:
        allocs.append(Allocation(
            fy=fy,
            task=fact.element,
            hours=0.0,
            cost=1000.0
        ))
    
    return allocs


def render(payload: UnifiedPayload) -> str:
    """
    Render annual fiscal year rollup report
    
    Args:
        payload: Unified payload with allocations
        
    Returns:
        Markdown formatted report
    """
    allocs = payload.allocations or _infer_allocations_from_facts(payload)
    
    # Aggregate by fiscal year and level
    by_fy = defaultdict(lambda: defaultdict(float))
    level = (payload.ui.level or "Total").lower()

    for a in allocs:
        # Determine aggregation key based on level
        key = {
            "resource": a.task or a.wbs or a.clin or "Resource",
            "task": a.task or "Task",
            "clin": a.clin or "CLIN",
            "wbs": a.wbs or "WBS",
            "ipt": a.ipt or "IPT",
            "total": "Total"
        }.get(level, "Total")
        
        by_fy[a.fy][key] += (a.cost or 0.0)

    # Build report
    lines = [
        f"# Annual Fiscal Year Report",
        f"",
        f"**Report Type:** Cost Rollup by {payload.ui.level or 'Total'}  ",
        f"**Contract Type:** {payload.ui.contract_type or 'Not Specified'}  ",
        f"**Generated (UTC):** {datetime.utcnow().isoformat()}Z  ",
        f""
    ]
    
    # Add RFP info if present
    if payload.rfp:
        lines.extend([
            f"## RFP Information",
            f"- **Title:** {payload.rfp.title or 'N/A'}",
            f"- **Customer:** {payload.rfp.customer or 'N/A'}",
            f"- **RFP ID:** {payload.rfp.rfp_id or 'N/A'}",
            f""
        ])
    
    # Add summary statistics
    total_cost = sum(sum(bucket.values()) for bucket in by_fy.values())
    lines.extend([
        f"## Summary",
        f"- **Total Program Cost:** ${total_cost:,.2f}",
        f"- **Fiscal Years:** {', '.join(sorted(by_fy.keys()))}",
        f"- **Number of Elements:** {len(set(k for bucket in by_fy.values() for k in bucket.keys()))}",
        f""
    ])

    # Add detailed breakdown by fiscal year
    lines.append(f"## Cost Breakdown by Fiscal Year")
    lines.append(f"")
    
    # Create summary table
    all_keys = set()
    for bucket in by_fy.values():
        all_keys.update(bucket.keys())
    
    if all_keys:
        # Table header
        lines.append("| Category | " + " | ".join(sorted(by_fy.keys())) + " | Total |")
        lines.append("|----------|" + "--------|" * (len(by_fy) + 1))
        
        # Table rows
        for key in sorted(all_keys):
            row = [key]
            row_total = 0
            for fy in sorted(by_fy.keys()):
                value = by_fy[fy].get(key, 0)
                row.append(f"${value:,.2f}")
                row_total += value
            row.append(f"${row_total:,.2f}")
            lines.append("| " + " | ".join(row) + " |")
        
        # Total row
        lines.append("| **TOTAL** | " + " | ".join(
            [f"**${sum(by_fy[fy].values()):,.2f}**" for fy in sorted(by_fy.keys())] +
            [f"**${total_cost:,.2f}**"]
        ) + " |")
    
    # Add assumptions if present
    if payload.assumptions:
        lines.extend([
            "",
            "## Assumptions",
            ""
        ])
        for i, assumption in enumerate(payload.assumptions, 1):
            lines.append(f"{i}. {assumption.text}")
            if assumption.source:
                lines.append(f"   - Source: {assumption.source}")
    
    # Add HEFs if present
    if payload.hefs:
        lines.extend([
            "",
            "## Human Effort Factors (HEFs)",
            ""
        ])
        for hef in payload.hefs:
            lines.append(f"**Base Year:** {hef.basis_year}")
            lines.append("")
            lines.append("| Fiscal Year | Factor |")
            lines.append("|-------------|--------|")
            for fy, factor in sorted(hef.series.items()):
                lines.append(f"| {fy} | {factor:.3f} |")
    
    # Add validation results if present
    if payload.audit.validations or payload.audit.conflicts:
        lines.extend([
            "",
            "## Validation Results",
            ""
        ])
        
        warnings = [e for e in payload.audit.validations if e.kind == "warning"]
        errors = [e for e in payload.audit.validations if e.kind == "error"]
        
        if errors:
            lines.append(f"### ❌ Errors ({len(errors)})")
            lines.append("")
            for error in errors:
                lines.append(f"- **{error.code}:** {error.message}")
        
        if warnings:
            lines.append(f"### ⚠️ Warnings ({len(warnings)})")
            lines.append("")
            for warning in warnings:
                lines.append(f"- **{warning.code}:** {warning.message}")
        
        if payload.audit.conflicts:
            lines.append(f"### 🔄 Conflicts ({len(payload.audit.conflicts)})")
            lines.append("")
            for conflict in payload.audit.conflicts:
                lines.append(f"- **{conflict.code}:** {conflict.message}")
    
    # Add footer
    lines.extend([
        "",
        "---",
        "*Generated by ProposalOS Report Generation Engine v1.0*"
    ])
    
    return "\n".join(lines) + "\n"
#!/usr/bin/env python3
# annual_fiscal_year_report_assembler.py
"""
Assemble Annual Fiscal Year Cost Breakdown Report (Markdown) from KB facts.
Supports levels: CLIN, Resource, Task, Total, Custom (e.g., IPT).
Usage:
  python annual_fiscal_year_report_assembler.py --in cleaned.json --out Annual_FY_Report.md --level "CLIN" --program "ACME SatCom"
"""
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--level", default="Total", help="Breakdown level: CLIN, Resource, Task, Total, IPT")
    ap.add_argument("--program", default="Program X")
    args = ap.parse_args()

    data = json.loads(Path(args.inp).read_text())
    facts = data.get("facts", [])

    # Aggregate costs by fiscal year and level
    fy_costs = defaultdict(lambda: defaultdict(float))
    # Example aggregation (placeholder logic)
    for fact in facts:
        element = fact['element']
        # Assume some FY mapping; in real, parse from data
        fy = "FY2025"  # Placeholder
        cost = 1000.0  # Placeholder from fact
        key = element if args.level == "Resource" else "Total"
        fy_costs[fy][key] += cost

    lines = [f"# Annual Fiscal Year Report - {args.program}"]
    lines.append(f"**Level:** {args.level}  \n**Generated:** {datetime.utcnow().isoformat()}Z\n")

    for fy, costs in fy_costs.items():
        lines.append(f"## {fy}")
        for key, total in costs.items():
            lines.append(f"- {key}: ${total:,.2f}")
        # Add labor, subs, travel, indirects, fee as per description

    Path(args.outp).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote Annual FY Report to {args.outp}")

if __name__ == "__main__":
    main()
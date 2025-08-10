
#!/usr/bin/env python3
# sandbox_cost_volume_assembler_v2.py
"""
Cost Volume assembler (tables + math)
- Loads cleaned KB (optional, for citations) and a JSON of numeric inputs
- Renders Markdown tables for Labor, Materials, Subcontracts, Travel + summary
Usage:
  python sandbox_cost_volume_assembler_v2.py --inputs demo_inputs.json --kb KB_cleaned.json --out Cost_Volume_Tables.md
"""

import json, argparse
from pathlib import Path
from datetime import datetime

import pandas as pd

from sandbox_cost_algorithms import (
    LaborLine, MaterialLine, SubcontractLine, TravelLine, RateSet,
    build_labor_table, build_materials_table, build_subcontracts_table, build_travel_table,
    compute_bases_and_fee
)

def md_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".2f")

def load_inputs(p: Path):
    data = json.loads(p.read_text())
    rates = RateSet(**data["rates"])
    labor = [LaborLine(**x) for x in data.get("labor", [])]
    materials = [MaterialLine(**x) for x in data.get("materials", [])]
    subks = [SubcontractLine(**x) for x in data.get("subcontracts", [])]
    travel = [TravelLine(**x) for x in data.get("travel", [])]
    fee = float(data.get("fee_pct", 0.1))
    exclude_subk_from_fee = bool(data.get("exclude_subk_from_fee", False))
    return rates, labor, materials, subks, travel, fee, exclude_subk_from_fee, data.get("meta", {})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--kb", required=False)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rates, labor, materials, subks, travel, fee_pct, excl_subk_fee, meta = load_inputs(Path(args.inputs))

    # Build tables
    df_labor, tot_labor = build_labor_table(labor, rates, years_from_base=0.0)
    df_mat, tot_mat = build_materials_table(materials)
    df_subk, tot_subk = build_subcontracts_table(subks)
    df_trv, tot_trv = build_travel_table(travel)
    totals = compute_bases_and_fee(tot_labor, tot_mat, tot_subk, tot_trv, rates, fee_pct, excl_subk_fee)

    lines = []
    title = meta.get("title","Cost Volume") + f" — Generated {datetime.utcnow().isoformat()}Z"
    lines.append(f"# {title}")
    lines.append("")
    lines.append("## Rates")
    lines.append(f"- Fringe: **{rates.fringe:.2%}**  \n- Overhead: **{rates.overhead:.2%}**  \n- G&A: **{rates.gna:.2%}**  \n- Escalation: **{rates.escalation:.2%}**")
    lines.append("")

    if len(df_labor):
        lines.append("## Direct Labor")
        lines.append(md_table(df_labor)); lines.append("")
    if len(df_mat):
        lines.append("## Direct Materials")
        lines.append(md_table(df_mat)); lines.append("")
    if len(df_subk):
        lines.append("## Subcontracts")
        lines.append(md_table(df_subk)); lines.append("")
    if len(df_trv):
        lines.append("## Travel")
        lines.append(md_table(df_trv)); lines.append("")

    # Summary
    lines.append("## Cost Summary")
    summ = [
        ["Burdened Labor $", tot_labor["burdened_labor"]],
        ["Materials $", tot_mat["total_material"]],
        ["Subcontracts $", tot_subk["total_subk"]],
        ["Travel $", tot_trv["total_travel"]],
        ["G&A Base $", totals["base_gna"]],
        ["G&A $", totals["gna_amt"]],
        ["Fee Base $", totals["fee_base"]],
        ["Fee $", totals["fee_amt"]],
        ["Grand Total $", totals["grand_total"]],
    ]
    df_sum = pd.DataFrame(summ, columns=["Item","Amount ($)"])
    lines.append(md_table(df_sum))

    # Optional: citations section from KB
    if args.kb and Path(args.kb).exists():
        import itertools, json
        kb = json.loads(Path(args.kb).read_text())
        facts = kb["facts"] if isinstance(kb, dict) and "facts" in kb else kb
        lines.append("\n## Regulatory Citations (from KB)")
        for eoc, group in itertools.groupby(sorted(facts, key=lambda x: x.get("element","")), key=lambda x: x.get("element","")):
            lines.append(f"### {eoc}")
            any_cite = False
            for f in group:
                for s in f.get("regulatory_support", []):
                    any_cite = True
                    q = (s.get("quote","") or "").replace("\\n"," ").strip()
                    lines.append(f"- {s.get('reg_title','')}, {s.get('reg_section','')}: “{q}” ({s.get('url','')})")
            if not any_cite:
                lines.append("- _No citations present_")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# cost_volume_assembler.py
"""
Assemble a skeletal Cost Volume (Markdown) from KB facts.
- Groups by Element of Cost
- Inserts compliance citation bullets and placeholders for BOE inputs
Usage:
  python cost_volume_assembler.py --in cleaned.json --out Cost_Volume.md --program "ACME SatCom" --contract "CPFF"
"""
import json, argparse
from pathlib import Path
from datetime import datetime

TEMPLATES = {
"Direct Labor": """#### Direct Labor
- Classification: Direct
- Basis of Estimate (placeholder): Describe skill mix, hours derivation, labor categories.
- Compliance: FAR 31.201-2 (allowability), CAS 402 consistency (as applicable).
{citations}
""",
"Direct Materials": """#### Direct Materials
- Classification: Direct
- Basis of Estimate (placeholder): BOM summary, priced vendor quotes, make/buy notes.
- Compliance: FAR 31.205-26 material costs (as applicable).
{citations}
""",
"Subcontracts": """#### Subcontracts
- Classification: Direct
- Basis of Estimate (placeholder): SubK evaluations, cost/price analysis, flowdowns.
- Compliance: FAR 15.404-3 Subcontract pricing considerations.
{citations}
""",
"G&A": """#### G&A
- Classification: Indirect
- Basis (placeholder): Describe pool/base, provisional vs. forward pricing rate.
- Compliance: CAS 410 allocation; FAR 31.203 indirect costs.
{citations}
""",
"Overhead": """#### Overhead
- Classification: Indirect
- Basis (placeholder): Engineering/Manufacturing overhead pools, base rationale.
- Compliance: FAR 31.203; Disclosure Statement alignment (if CAS-covered).
{citations}
""",
"Fringe": """#### Fringe
- Classification: Indirect
- Basis (placeholder): Benefits structure, actuary schedules, fringe base.
- Compliance: FAR 31.205-6 compensation (as applicable).
{citations}
""",
"Travel": """#### Travel
- Classification: Direct
- Basis (placeholder): Trip count, per-diem/mileage assumptions, JTR references.
- Compliance: FAR 31.205-46 travel costs; DFARS 231.205-46 (DoD).
{citations}
""",
"Fee": """#### Fee/Profit
- Classification: Fee
- Basis (placeholder): Weighted guidelines (DoD) or price analysis rationale.
- Compliance: FAR 15.404-4 profit.
{citations}
"""
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--program", default="Program X")
    ap.add_argument("--contract", default="Contract Type TBD")
    args = ap.parse_args()

    data = json.loads(Path(args.inp).read_text())
    facts = data["facts"] if isinstance(data, dict) else data

    by_elem = {}
    for f in facts:
        e = f.get("element","")
        by_elem.setdefault(e, []).append(f)

    lines = []
    lines.append(f"# Cost Volume — {args.program}")
    lines.append(f"_Contract Type: {args.contract}_  \n_Generated: {datetime.utcnow().isoformat()}Z_\n")
    lines.append("## Basis of Estimate Summary (Skeletal)")
    wanted_order = ["Direct Labor","Direct Materials","Subcontracts","Travel","Overhead","Fringe","G&A","Fee"]
    for e in wanted_order:
        if e not in by_elem: 
            continue
        cites = []
        for f in by_elem[e]:
            for s in f.get("regulatory_support", []):
                q = s.get("quote","").replace("\n"," ").strip()
                cites.append(f"- {s.get('reg_title','')}, {s.get('reg_section','')}: “{q}” (conf {s.get('confidence',0):.2f}) {s.get('url','')}")
        cite_block = "\n".join(cites) if cites else "- _No citations extracted yet_"
        tmpl = TEMPLATES.get(e, f"#### {e}\n(citations below)\n{{citations}}\n")
        lines.append(tmpl.format(citations=cite_block))

    Path(args.outp).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote Cost Volume skeleton → {args.outp}")

if __name__ == "__main__":
    main()

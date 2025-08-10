# updated_sandbox_validate_kb.py
#!/usr/bin/env python3
# validate_kb.py
"""
Validate and normalize ProposalOS RFP KB facts:
- Enforce <=25-word quote limit
- Apply citation sanity scoring (element↔section keyword gating)
- Dedupe & merge duplicate facts by (doc_id, section, element, classification)
- Wrap in schema envelope with metadata
Usage:
  python validate_kb.py --in path/to/RFP_KB_Facts_*.json --out cleaned.json --schema 1.1.0
"""
import json, re, argparse, math
from pathlib import Path
from datetime import datetime, timezone

WORD_RE = re.compile(r"[A-Za-z0-9']+")

ELEMENT_HINTS = {
    "Direct Labor": ["labor","direct","personnel","hours","wage","salary","staff"],
    "Direct Materials": ["material","supply","part","component"],
    "Subcontracts": ["subcontract","vendor","supplier","teaming"],
    "G&A": ["general","administrative","g&a"],
    "Overhead": ["overhead","indirect","allocation","burden"],
    "Fringe": ["fringe","benefit","leave","insurance","retirement"],
    "Travel": ["travel","lodging","per diem","mileage","airfare"],
    "Fee": ["fee","profit","award"]
}

def wcount(s:str)->int:
    return len(WORD_RE.findall(s or ""))

def trunc25(s:str)->str:
    return " ".join(WORD_RE.findall((s or ""))[:25])

def sanity_score(element:str, reg_title:str, reg_section:str, quote:str, contract_type: str)->float:
    hay = " ".join([reg_title or "", reg_section or "", quote or ""]).lower()
    hints = [h.lower() for h in ELEMENT_HINTS.get(element, [])]
    if not hints: return 0.9
    hits = sum(1 for h in hints if h in hay)
    if element == "Fee" and contract_type == "FFP" and "cost" in hay:
        return 0.5  # Penalize fee as cost in FFP
    if hits == 0: return 0.65
    if hits == 1: return 0.85
    return 1.0

def safe_float(x, default=0.5):
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return max(0.0, min(1.0, v))
    except Exception:
        return default

def dedupe_merge(facts):
    idx = {}
    merged = []
    for f in facts:
        src = f.get("source", {})
        key = (src.get("doc_id",""), src.get("section",""), f.get("element",""), f.get("classification",""))
        if key not in idx:
            idx[key] = len(merged)
            merged.append(f)
        else:
            i = idx[key]
            tgt = merged[i]
            # Merge regulatory_support unique by (reg_title, reg_section, quote)
            seen = {(s.get("reg_title",""), s.get("reg_section",""), s.get("quote","")) for s in tgt.get("regulatory_support",[])}
            for s in f.get("regulatory_support",[]):
                tup = (s.get("reg_title",""), s.get("reg_section",""), s.get("quote",""))
                if tup not in seen:
                    tgt.setdefault("regulatory_support",[]).append(s)
                    seen.add(tup)
            # Keep higher confidence at fact-level if present
            if f.get("confidence",0) > tgt.get("confidence",0):
                tgt["confidence"] = f["confidence"]
            merged[i] = tgt
    return merged

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--schema", default="1.1.0")
    ap.add_argument("--mode", default="validate_only")
    ap.add_argument("--model", default="gemini-2.5-pro")
    ap.add_argument("--contract-type", default="CPFF", help="Contract type (e.g., CPFF, FFP)")
    args = ap.parse_args()

    data = json.loads(Path(args.inp).read_text())
    # Old dumps might be a raw list; allow envelope or list
    if isinstance(data, dict) and "facts" in data:
        facts = data["facts"]
    else:
        facts = data

    cleaned = []
    for f in facts:
        # enforce quote limit + sanity per citation
        for s in f.get("regulatory_support", []):
            s["quote"] = trunc25(s.get("quote",""))
            base = s.get("confidence", 0.5)
            pen = sanity_score(f.get("element",""), s.get("reg_title",""), s.get("reg_section",""), s.get("quote",""), args.contract_type)
            s["confidence"] = safe_float(base * pen)
            s["validated"] = bool(pen >= 0.95)
        # optional overall confidence as max of supports
        if f.get("regulatory_support"):
            f["confidence"] = max(safe_float(s.get("confidence",0.0)) for s in f["regulatory_support"])
        cleaned.append(f)

    merged = dedupe_merge(cleaned)

    envelope = {
        "schema_version": args.schema,
        "extraction_mode": args.mode,
        "model": args.model,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "facts": merged
    }
    Path(args.outp).write_text(json.dumps(envelope, indent=2))
    print(f"Wrote cleaned KB with {len(merged)} facts → {args.outp}")

if __name__ == "__main__":
    main()
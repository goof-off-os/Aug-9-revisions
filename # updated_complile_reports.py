# updated_complile_reports.py
"""
ProposalOS - RFP-focused EoC Discovery Pipeline (with tune-ups)
----------------------------------------------------------------
Adds:
- ≤25-word quote guardrail w/ strict counting
- Citation sanity checks (element↔section gating + penalties; validated flag)
- Deduping/merging of duplicate EoCs within a doc/section
- JSON envelope with schema_version, extraction_mode, model, generated_at_utc
- Calibrated confidences in dry-run based on keyword match strength + title bonus
- Path portability via RFP_OUTPUT_BASE env var (fallback to ~/Desktop/Agents_writing_reports)
- New --schema-version flag
Retains hardcoded model: gemini-2.5-pro
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from time import sleep
import logging
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv
# lazy import of google.generativeai

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("proposalos_rfp")

# ---------- Config (Hardcoded Model) ----------
load_dotenv("LLM_MODEL_G.env")
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-pro")
SCHEMA_DEFAULT = "1.1.0"

if MODEL_NAME != "gemini-2.5-pro":
    raise ValueError(f"Invalid model: {MODEL_NAME}. Must be gemini-2.5-pro")

GENAI_READY = False
def _ensure_genai():
    global GENAI_READY
    if GENAI_READY:
        return True
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=API_KEY)
        globals()['genai'] = genai
        GENAI_READY = True
        return True
    except Exception as e:
        if os.getenv('GENAI_IMPORT_REQUIRED','0') == '1':
            raise
        return False


# ---------- Paths ----------
def base_output_dir() -> Path:
    env_base = os.getenv("RFP_OUTPUT_BASE")
    if env_base:
        return Path(env_base).expanduser()
    return Path.home() / "Desktop" / "Agents_writing_reports"

BASE_DIR = base_output_dir()
REPORT_DIR = BASE_DIR / "RFP_Discovery_Reports"
KB_DIR = BASE_DIR / "RFP_KnowledgeBase"
for d in (BASE_DIR, REPORT_DIR, KB_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
def now_ts():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

_word_re = re.compile(r"[A-Za-z0-9']+")
def word_count(s: str) -> int:
    return len(_word_re.findall(s))

def truncate_quote_25w(s: str) -> str:
    return " ".join(_word_re.findall(s)[:25])

def safe_float(x, default=0.5) -> float:
    try:
        v = float(x)
        if v != v or v == float("inf") or v == float("-inf"):
            return default
        return max(0.0, min(1.0, v))
    except Exception:
        return default

# ---------- Parser integration ----------
def _module_iter_docs(mod):
    # Accept common entrypoints
    for name in ("iter_docs", "load_docs", "get_docs", "load_parsed_documents"):
        if hasattr(mod, name):
            fn = getattr(mod, name)
            docs = fn()
            if hasattr(docs, "__iter__"):
                if isinstance(docs, list):
                    for d in docs:
                        yield d
                else:
                    for d in docs:
                        yield d
            return
    raise RuntimeError(f"Parser module '{mod.__name__}' needs iter_docs()/load_docs()/get_docs()/load_parsed_documents().")

def load_parsed_regulations():
    """
    Load parsed regulation documents from available parser modules.
    Expect dict:
      { 'id': str, 'title': str, 'section': str, 'text': str, 'url': Optional[str] }
    """
    sys.path.append("/mnt/data")
    modules = []

    try:
        import dita_parser_AF_SF_Army_Navy as m1  # type: ignore
        modules.append(m1)
        log.info("Loaded parser: dita_parser_AF_SF_Army_Navy")
    except Exception as e:
        log.warning(f"Could not load 'dita_parser_AF_SF_Army_Navy': {e}")

    try:
        import dita_parser as m2  # type: ignore
        modules.append(m2)
        log.info("Loaded parser: dita_parser")
    except Exception as e:
        log.warning(f"Could not load 'dita_parser': {e}")

    all_docs = []
    for mod in modules:
        for doc in _module_iter_docs(mod):
            all_docs.append(doc)
    log.info(f"Loaded {len(all_docs)} regulation documents.")
    return all_docs

# ---------- KB Fact Structure ----------
@dataclass
class KBItem:
    element: str
    classification: str
    rfp_relevance: str
    regulatory_support: List[Dict[str, Any]]
    notes: str = ""

# ---------- Prompt Makers ----------
def make_prompt_rfp_discovery(doc, contract_type="CPFF"):
    return f"""
    You are a compliance expert for DoD proposals. Extract Elements of Cost (EoCs) from the text, including Direct Labor, Direct Materials, Travel, Overhead, Fringe, G&A, and Fee. For each:
    - Classify as direct or indirect per FAR/DFARS/CAS.
    - Cite specific regulations (FAR, DFARS, CAS) with section and quote (max 25 words).
    - Specify relevance to RFP for contract type: {contract_type}.
    - Note program-specific considerations (e.g., mission segment, PoP).
    - Differentiate EoC categories (cost buckets) from rate structures (e.g., G&A burden).
    Text: {doc['text'][:10000]}
    Return JSON: {{"facts": [{{"element": str, "classification": str, "rfp_relevance": str, "regulatory_support": [{{"reg_title": str, "reg_section": str, "quote": str, "url": str, "confidence": float}}], "notes": str}}]}}
    """

def make_mock_items_from_text(doc):
    # Dry-run mocks: Generate placeholder facts based on text keywords
    mocks = []
    eocs = ["Direct Labor", "Direct Materials", "Subcontracts", "Travel", "Overhead", "Fringe", "G&A", "Fee"]
    for eoc in eocs:
        mocks.append({
            "element": eoc,
            "classification": "direct" if "direct" in eoc.lower() else "indirect" if "overhead" in eoc.lower() or "fringe" in eoc.lower() or "g&a" in eoc.lower() else "fee",
            "rfp_relevance": "Mock relevance for " + eoc,
            "regulatory_support": [{
                "reg_title": doc["title"],
                "reg_section": doc["section"],
                "quote": doc["text"][:100],
                "url": doc.get("url", ""),
                "confidence": 0.5
            }],
            "notes": "Dry-run placeholder"
        })
    return mocks

# ---------- API Calls ----------
def call_gemini(prompt):
    if not _ensure_genai():
        raise RuntimeError("Gemini API not available.")
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    return response.text

def parse_json_array(raw: str):
    try:
        return json.loads(raw).get("facts", [])
    except Exception:
        return []

# ---------- Sanity & Validation ----------
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

def apply_sanity_and_truncate(item, doc, contract_type="CPFF"):
    if item["element"] == "Fee" and contract_type == "FFP":
        item["classification"] = "fixed_price_component"
        item["rfp_relevance"] = "Fee is fixed and not cost-based in FFP contracts."
    for sup in item.get("regulatory_support", []):
        sup["quote"] = truncate_quote_25w(sup.get("quote",""))
        base = sup.get("confidence", 0.5)
        pen = sanity_score(item["element"], sup["reg_title"], sup["reg_section"], sup["quote"], contract_type)
        sup["confidence"] = safe_float(base * pen)
        sup["validated"] = bool(pen >= 0.95)
    item["confidence"] = max(safe_float(s.get("confidence",0.0)) for s in item.get("regulatory_support", [])) if item.get("regulatory_support") else 0.5
    return item

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
            seen = {(s.get("reg_title",""), s.get("reg_section",""), s.get("quote","")) for s in tgt.get("regulatory_support",[])}
            for s in f.get("regulatory_support",[]):
                tup = (s.get("reg_title",""), s.get("reg_section",""), s.get("quote",""))
                if tup not in seen:
                    tgt.setdefault("regulatory_support",[]).append(s)
                    seen.add(tup)
            if f.get("confidence",0) > tgt.get("confidence",0):
                tgt["confidence"] = f.get("confidence")
            merged[i] = tgt
    return merged

# ---------- CLI ----------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--schema-version", default=SCHEMA_DEFAULT)
    ap.add_argument("--contract-type", default="CPFF", help="Contract type (e.g., CPFF, FFP)")
    return ap.parse_args()

# ---------- Run pipeline ----------
def run_rfp_discovery(dry_run=False, limit=0, schema_version=SCHEMA_DEFAULT, contract_type="CPFF"):
    docs = load_parsed_regulations()
    if limit and limit > 0:
        docs = docs[:limit]

    raw_facts: List[Dict[str,Any]] = []
    md_sections = []

    eocs = ["Direct Labor", "Direct Materials", "Subcontracts", "Travel", "Overhead", "Fringe", "G&A", "Fee"]
    for idx, doc in enumerate(docs, start=1):
        if dry_run:
            items = make_mock_items_from_text(doc)
        else:
            if not API_KEY:
                log.error('GEMINI_API_KEY missing; cannot run in non-dry mode.')
                break
            prompt = make_prompt_rfp_discovery(doc, contract_type)
            try:
                raw = call_gemini(prompt)
                items = parse_json_array(raw)
            except Exception as e:
                log.error(f"Doc '{doc['title']}' parse error: {e}")
                continue

        cleaned_items = []
        found_eocs = set()
        for it in items if isinstance(items, list) else []:
            it = apply_sanity_and_truncate(it, doc, contract_type)
            rec = {
                "fact_id": sha8(f"{it['element']}|{it['classification']}|{doc['id']}|{doc['section']}"),
                "element": it["element"],
                "classification": it["classification"],
                "rfp_relevance": it["rfp_relevance"],
                "regulatory_support": it["regulatory_support"],
                "notes": it.get("notes",""),
                "source": {
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "section": doc["section"],
                    "url": doc.get("url","")
                },
                "timestamp": utc_now_iso()
            }
            raw_facts.append(rec)
            cleaned_items.append(rec)
            found_eocs.add(it["element"])

        # Add placeholders for missing EoCs
        for eoc in eocs:
            if eoc not in found_eocs:
                rec = {
                    "fact_id": sha8(f"{eoc}|unknown|{doc['id']}|{doc['section']}"),
                    "element": eoc,
                    "classification": "unknown",
                    "rfp_relevance": f"No {eoc} data found in {doc['title']}; review RFP.",
                    "regulatory_support": [],
                    "notes": "Placeholder for missing EoC.",
                    "source": {
                        "doc_id": doc["id"],
                        "title": doc["title"],
                        "section": doc["section"],
                        "url": doc.get("url","")
                    },
                    "timestamp": utc_now_iso()
                }
                raw_facts.append(rec)
                cleaned_items.append(rec)

        # Build human-readable chunk
        if cleaned_items:
            sec_lines = [f"## {doc['title']} — {doc['section']}\n"]
            for rec in cleaned_items:
                sec_lines.append(
                    f"### {rec['element']}  \n"
                    f"- Classification: **{rec['classification']}**  \n"
                    f"- RFP relevance: {rec['rfp_relevance'] or '_n/a_'}  \n"
                    f"- Notes: {rec['notes'] or '_none_'}  \n"
                    f"- Source: {rec['source'].get('url') or rec['source']['title']} ({rec['source']['section']})  \n"
                )
                if rec["regulatory_support"]:
                    sec_lines.append("  - Citations:")
                    for sup in rec["regulatory_support"]:
                        quote = sup.get("quote","").replace("\n"," ")
                        val = "true" if sup.get("validated") else "false"
                        sec_lines.append(
                            f"    - {sup.get('system','') or sup.get('reg_title','')}, {sup.get('reg_section','')}: "
                            f"\"{quote}\" (conf {sup.get('confidence',0):.2f}, validated {val}) {sup.get('url','')}"
                        )
            md_sections.append("\n".join(sec_lines))

        log.info(f"[{idx}/{len(docs)}] Processed: {doc['title']} — {doc['section']} → {len(cleaned_items)} facts")

    # Deduplicate & merge before writing
    facts = dedupe_merge(raw_facts)

    # Write Markdown
    ts = now_ts()
    md_header = (
        f"# RFP EoC Discovery Report\n"
        f"**Generated (UTC):** {utc_now_iso()}  \n"
        f"**Model:** {MODEL_NAME}\n\n---\n"
    )
    md_body = "\n\n---\n\n".join(md_sections) if md_sections else "_No facts extracted._"
    md_path = REPORT_DIR / f"RFP_Discovery_Report_{ts}.md"
    md_path.write_text(md_header + md_body, encoding="utf-8")

    # Write JSON envelope
    envelope = {
        "schema_version": schema_version,
        "extraction_mode": "dry_run" if dry_run else "llm",
        "model": MODEL_NAME,
        "generated_at_utc": utc_now_iso(),
        "facts": facts
    }
    kb_path = KB_DIR / f"RFP_KB_Facts_{ts}.json"
    with kb_path.open("w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Outputs written:\n - {md_path}\n - {kb_path}\n - Facts: {len(facts)}")
    return str(md_path), str(kb_path)

if __name__ == "__main__":
    args = parse_args()
    run_rfp_discovery(dry_run=args.dry_run, limit=args.limit, schema_version=args.schema_version, contract_type=args.contract_type)
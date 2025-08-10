#!/usr/bin/env python3
"""
ProposalOS - RFP-focused EoC Discovery Pipeline
------------------------------------------------
Generates two outputs per run:
  1) Human-readable compiled report (Markdown)
  2) Machine-ingestible knowledge base JSON (facts with attribution)

Scope:
- Focus on RFP (exclude ROM/RFI for now)
- Force agents to DISCOVER Elements of Cost (EoC), classify Direct/Indirect in RFP context,
  and attach regulatory citations (FAR/DFARS/CAS/Agency supplements like AFARS/DAFFARS/NMCARS)
- Hardcode Gemini model to gemini-2.5-pro (do not auto-swap)

Inputs assumed:
- Parsed regulation content available via local parser modules, e.g.:
  /mnt/data/dita_parser_AF_SF_Army_Navy.py  (uploaded by user)
  /mnt/data/dita_parser.py                  (user's general parser)

Environment:
- LLM_MODEL_G.env with GEMINI_API_KEY and MODEL_NAME=gemini-2.5-pro
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from time import sleep
import logging
import argparse

from dotenv import load_dotenv
import google.generativeai as genai

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("proposalos_rfp")

# ---------- Config (Hardcoded Model) ----------
load_dotenv("LLM_MODEL_G.env")
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-pro")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY missing in LLM_MODEL_G.env")
if MODEL_NAME != "gemini-2.5-pro":
    raise ValueError(f"Invalid model: {MODEL_NAME}. Must be gemini-2.5-pro")

genai.configure(api_key=API_KEY)

# ---------- Paths ----------
DESKTOP_PATH = Path.home() / "Desktop"
BASE_DIR = DESKTOP_PATH / "Agents_writing_reports"
REPORT_DIR = BASE_DIR / "RFP_Discovery_Reports"
KB_DIR = BASE_DIR / "RFP_KnowledgeBase"
for d in (BASE_DIR, REPORT_DIR, KB_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
def now_ts():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r'[:/\\&]', '-', s)
    s = re.sub(r'[^a-z0-9\\-]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:200]

def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]

# ---------- Parser integration ----------
def _module_iter_docs(mod):
    # Try common entrypoints
    for name in ("iter_docs", "load_docs", "get_docs"):
        if hasattr(mod, name):
            fn = getattr(mod, name)
            docs = fn()
            if hasattr(docs, "__iter__"):
                # normalize to iterator of dicts
                if isinstance(docs, list):
                    for d in docs:
                        yield d
                else:
                    for d in docs:
                        yield d
            return
    raise RuntimeError(f"Parser module '{mod.__name__}' needs an adapter exposing iter_docs()/load_docs()/get_docs().")

def load_parsed_regulations():
    """
    Load parsed regulation documents from available parser modules.
    Each yielded doc should be a dict with at least:
      { 'id': str, 'title': str, 'section': str, 'text': str, 'url': Optional[str] }
    """
    sys.path.append("/mnt/data")  # ensure uploaded modules are importable
    modules = []
    loaded = []

    # Primary module uploaded by user
    try:
        import dita_parser_AF_SF_Army_Navy as m1  # type: ignore
        modules.append(m1)
        log.info("Loaded parser: dita_parser_AF_SF_Army_Navy")
    except Exception as e:
        log.warning(f"Could not load 'dita_parser_AF_SF_Army_Navy': {e}")

    # General parser module
    try:
        import dita_parser as m2  # type: ignore
        modules.append(m2)
        log.info("Loaded parser: dita_parser")
    except Exception as e:
        log.info("Optional 'dita_parser' not found (ok).")

    if not modules:
        raise RuntimeError("No parser modules found. Please ensure your DITA parsers are importable.")

    for mod in modules:
        for doc in _module_iter_docs(mod):
            if not isinstance(doc, dict):
                continue
            text = doc.get("text") or ""
            title = doc.get("title") or ""
            if not text.strip():
                continue
            loaded.append({
                "id": str(doc.get("id") or sha8(title + text[:100])),
                "title": title,
                "section": str(doc.get("section") or ""),
                "text": text,
                "url": doc.get("url") or ""
            })
    if not loaded:
        raise RuntimeError("Parser modules loaded but returned no documents with text.")
    log.info(f"Parsed regulations loaded: {len(loaded)} docs")
    return loaded

# ---------- Prompting (strict JSON) ----------
JSON_INSTRUCTIONS = """
Return strictly valid JSON ONLY, matching this schema per ITEM (no markdown, no prose around it).

{
  "element": "<canonical element name discovered (e.g., Direct Labor, G&A, Travel)>",
  "classification": "<direct|indirect|fee|ambiguous>",
  "rfp_relevance": "<short sentence describing how this element is treated in RFP context>",
  "regulatory_support": [
    {
      "reg_title": "<FAR or Agency title>",
      "reg_section": "<e.g., FAR 31.201-2>",
      "quote": "<=25 words exact quote>",
      "url": "<if available>",
      "confidence": 0.0
    }
  ],
  "notes": "<optional>"
}
Rules:
- If unsure of classification, use "ambiguous" with explanation in notes.
- Each regulatory_support item MUST include a <=25-word quote and a section locator.
"""

def make_prompt_rfp_discovery(doc):
    preface = (
        "You are extracting Elements of Cost (EoC) and their Direct/Indirect classification strictly in the context of RFP preparation.\n"
        "Distinguish cost categories (EoC) from pricing outcomes (fee/profit). If fee is mentioned, classify as 'fee'.\n"
        "Use FAR/DFARS/CAS/Agency supplements (AFARS/DAFFARS/NMCARS) found in the provided text to justify.\n"
    )
    excerpt = doc["text"]
    # Trim long text to keep prompts manageable
    if len(excerpt) > 8000:
        excerpt = excerpt[:8000]
    return (
        f"{preface}\n"
        f"Document: {doc['title']} | Section: {doc['section']} | URL: {doc.get('url','')}\n\n"
        f"TEXT START\n{excerpt}\nTEXT END\n\n"
        f"{JSON_INSTRUCTIONS}\n"
        f"Extract up to 8 ITEMS from this text. Respond as a JSON array of item objects only."
    )

# ---------- Dry-run mock extraction ----------
EOC_KEYWORDS = [
    ("Direct Labor", "direct", r"\bdirect labor\b"),
    ("Travel", "direct", r"\btravel\b"),
    ("Direct Materials", "direct", r"\bdirect materials?\b"),
    ("Subcontracts", "direct", r"\bsubcontracts?\b"),
    ("G&A", "indirect", r"\bg\&a\b|\bg and a\b|general\s*&\s*administrative"),
    ("Overhead", "indirect", r"\boverhead\b|\boh\b"),
    ("Fringe", "indirect", r"\bfringe\b"),
    ("Fee", "fee", r"\bfee\b|\bprofit\b"),
]

def _first_quote(text, max_words=25):
    words = text.strip().split()
    return " ".join(words[:max_words])

def make_mock_items_from_text(doc):
    import re as _re
    text = doc.get("text","")
    lower = text.lower()
    items = []
    for name, cls, pattern in EOC_KEYWORDS:
        if _re.search(pattern, lower):
            items.append({
                "element": name,
                "classification": cls,
                "rfp_relevance": f"{name} treated as {cls} in RFP cost structure when applicable.",
                "regulatory_support": [
                    {
                        "reg_title": doc.get("title",""),
                        "reg_section": doc.get("section",""),
                        "quote": _first_quote(text, 22),
                        "url": doc.get("url",""),
                        "confidence": 0.5
                    }
                ],
                "notes": ""
            })
    if not items:
        items = [{
            "element": "Unspecified Cost Element",
            "classification": "ambiguous",
            "rfp_relevance": "Text does not clearly specify EoC; mark as ambiguous for review.",
            "regulatory_support": [
                {
                    "reg_title": doc.get("title",""),
                    "reg_section": doc.get("section",""),
                    "quote": _first_quote(text, 18),
                    "url": doc.get("url",""),
                    "confidence": 0.2
                }
            ],
            "notes": "Dry-run placeholder"
        }]
    return items

# ---------- LLM call + JSON parse ----------
def call_gemini(prompt: str, temperature=0.2, top_p=0.9, max_tokens=2000, retries=3, dry_run=False, doc=None):
    if dry_run and doc is not None:
        # Return mocked JSON array as text
        items = make_mock_items_from_text(doc)
        return json.dumps(items, ensure_ascii=False, indent=2)
    for i in range(retries):
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            resp = model.generate_content(
                contents=prompt,
                generation_config={"temperature": temperature, "top_p": top_p, "max_output_tokens": max_tokens}
            )
            text = getattr(resp, "text", None)
            if not text:
                raise RuntimeError("Empty response from model.")
            return text
        except Exception as e:
            log.warning(f"Gemini call failed (attempt {i+1}/{retries}): {e}")
            sleep(1.5)
    raise RuntimeError("Gemini call failed after retries.")

def parse_json_array(raw_text: str):
    # Try to isolate the first [ ... ] block
    start = raw_text.find('[')
    end = raw_text.rfind(']') + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON array found in model output.")
    blob = raw_text[start:end]
    return json.loads(blob)

# ---------- CLI ----------
def parse_args():
    ap = argparse.ArgumentParser(description="ProposalOS RFP EoC Discovery")
    ap.add_argument("--dry-run", action="store_true", help="Simulate agent outputs without calling Gemini")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of docs processed (0 = no limit)")
    return ap.parse_args()

# ---------- Run pipeline ----------
def run_rfp_discovery(dry_run=False, limit=0):
    docs = load_parsed_regulations()

    kb_facts = []  # machine-ingestible
    md_sections = []  # human-readable

    if limit and limit > 0:
        docs = docs[:limit]

    for idx, doc in enumerate(docs, start=1):
        prompt = make_prompt_rfp_discovery(doc)
        try:
            raw = call_gemini(prompt, dry_run=dry_run, doc=doc)
            items = parse_json_array(raw)
        except Exception as e:
            log.error(f"Doc '{doc['title']}' parse error: {e}")
            continue

        # Normalize items and add attribution
        cleaned = []
        for it in items if isinstance(items, list) else []:
            if not isinstance(it, dict):
                continue
            element = str(it.get("element","")).strip()
            classification = str(it.get("classification","")).strip().lower()
            if classification not in ("direct","indirect","fee","ambiguous"):
                classification = "ambiguous"
            rfp_rel = str(it.get("rfp_relevance","")).strip()
            notes = str(it.get("notes","")).strip()
            support = it.get("regulatory_support", []) or []

            for sup in support:
                # Ensure minimal fields & attribution linkage
                sup["url"] = sup.get("url") or doc.get("url","")
                sup["reg_title"] = sup.get("reg_title","") or doc["title"]
                sup["reg_section"] = sup.get("reg_section","") or doc["section"]
                try:
                    sup["confidence"] = float(sup.get("confidence", 0.0))
                except Exception:
                    sup["confidence"] = 0.0

            fact_id = sha8(f"{element}|{classification}|{doc['id']}|{doc['section']}")
            rec = {
                "fact_id": fact_id,
                "element": element,
                "classification": classification,
                "rfp_relevance": rfp_rel,
                "regulatory_support": support,
                "notes": notes,
                "source": {
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "section": doc["section"],
                    "url": doc.get("url","")
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            cleaned.append(rec)
            kb_facts.append(rec)

        # Build human-readable section
        if cleaned:
            sec_lines = [f"## {doc['title']} — {doc['section']}\n"]
            for rec in cleaned:
                sec_lines.append(f"### {rec['element']}  \n"
                                 f"- Classification: **{rec['classification']}**  \n"
                                 f"- RFP relevance: {rec['rfp_relevance'] or '_n/a_'}  \n"
                                 f"- Notes: {rec['notes'] or '_none_'}  \n"
                                 f"- Source: {rec['source'].get('url') or rec['source']['title']} ({rec['source']['section']})  \n")
                if rec["regulatory_support"]:
                    sec_lines.append("  - Citations:")
                    for sup in rec["regulatory_support"]:
                        quote = sup.get("quote","").strip().replace("\n"," ")
                        sec_lines.append(f"    - {sup.get('reg_title','')}, {sup.get('reg_section','')}: \"{quote}\" "
                                         f"(conf {sup.get('confidence',0):.2f}) {sup.get('url','')}")
            md_sections.append("\n".join(sec_lines))

        log.info(f"[{idx}/{len(docs)}] Processed: {doc['title']} — {doc['section']} "
                 f"→ {len(cleaned)} facts")

    # Write outputs
    ts = now_ts()
    md_header = (
        f"# RFP EoC Discovery Report\n"
        f"**Generated (UTC):** {datetime.utcnow().isoformat()}  \n"
        f"**Model:** {MODEL_NAME}\n\n"
        f"---\n"
    )
    md_body = "\n\n---\n\n".join(md_sections) if md_sections else "_No facts extracted._"
    md_path = REPORT_DIR / f"RFP_Discovery_Report_{ts}.md"
    md_path.write_text(md_header + md_body, encoding="utf-8")

    kb_path = KB_DIR / f"RFP_KB_Facts_{ts}.json"
    with kb_path.open("w", encoding="utf-8") as f:
        json.dump(kb_facts, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Outputs written:\n - {md_path}\n - {kb_path}")
    return str(md_path), str(kb_path)

if __name__ == "__main__":
    args = parse_args()
    run_rfp_discovery(dry_run=args.dry_run, limit=args.limit)

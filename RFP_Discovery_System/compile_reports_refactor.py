#!/usr/bin/env python3
"""
ProposalOS — RFP-focused EoC Discovery Pipeline (Refactor)
-----------------------------------------------------------
This refactor tightens citation hygiene, makes paths configurable, and
adds validation + de-duplication to reduce noisy/incorrect facts.

Key changes vs your previous script:
- File name/typo fix (compile_reports.py) and structured CLI.
- Configurable output base dir via --outdir or $PROPOSALOS_OUTDIR (Desktop fallback).
- Added VALIDATION: quote length (<=25 words), allowed-support routing per element,
  and basic confidence flags (mismatch, missing URL/section).
- De-duplicates facts by (element, classification, doc_id, section) with stable ids.
- Safer dry-run generator: grabs a sentence containing the matched keyword.
- More robust module loading + better error messages.
- Optional --strict to DROP items with mismatched regulatory support instead of
  just flagging.

NOTE: The element→regulatory "allowlist" patterns are conservative.
Adjust ALLOWED_SUPPORT below to match your organization’s policy.
"""

from __future__ import annotations

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
from typing import Dict, Iterable, List, Tuple

from dotenv import load_dotenv

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None  # allows running in dry-run without the SDK

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("proposalos_rfp")

# ---------- Allowed-support routing (simple, conservative patterns) ----------
# Each element maps to a list of regex fragments expected in reg_section or reg_title.
ALLOWED_SUPPORT: Dict[str, List[str]] = {
    # FAR 31.205-46 (Travel) and DFARS 231.205-46 are typical anchors.
    "Travel": [r"31\.205-46", r"231\.205-46", r"Travel Costs"],
    # G&A allocation often rests on CAS 410 / 418 concepts.
    "G&A": [r"CAS\s*410", r"410\.50", r"Cost Accounting Standards", r"CAS\s*418"],
    # Direct Labor is generally a direct cost; look for FAR 31.202/31.203 or agency cost principles.
    "Direct Labor": [r"31\.202", r"31\.203", r"Direct\s+costs", r"labor"],
    # Direct Materials usually ties to FAR 31.202 and materials allowability.
    "Direct Materials": [r"31\.202", r"Direct\s+materials"],
    # Overhead is an indirect cost; allow CAS 418 or FAR 31.203.
    "Overhead": [r"31\.203", r"CAS\s*418", r"indirect\s+costs"],
    # Fringe benefits often live in FAR 31.205-6 (compensation) and related.
    "Fringe": [r"31\.205-6", r"compensation", r"fringe"],
    # Fee/Profit policy generally in FAR 15.404-4 or agency supplements.
    "Fee": [r"15\.404-4", r"profit", r"Weighted\s+Guidelines"],
}

# ---------- Paths ----------
def default_base_dir() -> Path:
    env = os.getenv("PROPOSALOS_OUTDIR")
    if env:
        return Path(env)
    # fallback to Desktop structure
    desk = Path.home() / "Desktop"
    return desk / "Agents_writing_reports"

# ---------- Helpers ----------
def now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]

# ---------- Parser integration ----------
PARSER_MODULE_CANDIDATES = (
    "dita_parser_AF_SF_Army_Navy",
    "dita_parser",
)

def _module_iter_docs(mod) -> Iterable[dict]:
    for name in ("iter_docs", "load_docs", "get_docs"):
        if hasattr(mod, name):
            fn = getattr(mod, name)
            docs = fn()
            if hasattr(docs, "__iter__"):
                yield from list(docs)
                return
    raise RuntimeError(f"Parser module '{mod.__name__}' needs iter_docs/load_docs/get_docs().")


def load_parsed_regulations() -> List[dict]:
    sys.path.append("/mnt/data")  # ensure uploaded modules are importable
    loaded: List[dict] = []
    errors: List[str] = []

    for name in PARSER_MODULE_CANDIDATES:
        try:
            mod = __import__(name)
            log.info(f"Loaded parser: {name}")
            for doc in _module_iter_docs(mod):
                if not isinstance(doc, dict):
                    continue
                text = (doc.get("text") or "").strip()
                title = str(doc.get("title") or "").strip()
                if not text:
                    continue
                loaded.append({
                    "id": str(doc.get("id") or sha8(title + text[:100])),
                    "title": title,
                    "section": str(doc.get("section") or ""),
                    "text": text,
                    "url": doc.get("url") or ""
                })
        except Exception as e:
            errors.append(f"{name}: {e}")

    if not loaded:
        hint = "; ".join(errors) or "no parser modules found"
        raise RuntimeError(f"No regulation docs loaded — {hint}.")

    log.info(f"Parsed regulations loaded: {len(loaded)} docs")
    return loaded

# ---------- Prompting (strict JSON) ----------
JSON_INSTRUCTIONS = r"""
Return strictly valid JSON ONLY, matching this schema per ITEM (no markdown, no prose around it).
[
  {
    "element": "<canonical element name discovered (e.g., Direct Labor, G&A, Travel)>",
    "classification": "<direct|indirect|fee|ambiguous>",
    "rfp_relevance": "<short sentence describing how this element is treated in RFP context>",
    "regulatory_support": [
      {
        "reg_title": "<FAR/DFARS/CAS/Agency title>",
        "reg_section": "<e.g., FAR 31.201-2>",
        "quote": "<=25 words exact quote>",
        "url": "<if available>",
        "confidence": 0.0
      }
    ],
    "notes": "<optional>"
  }
]
Rules:
- If unsure of classification, use "ambiguous" with explanation in notes.
- Each regulatory_support item MUST include a <=25-word quote and a section locator.
"""


def make_prompt_rfp_discovery(doc: dict) -> str:
    preface = (
        "You are extracting Elements of Cost (EoC) and their Direct/Indirect classification strictly in the context of RFP preparation.\n"
        "Distinguish cost categories (EoC) from pricing outcomes (fee/profit). If fee is mentioned, classify as 'fee'.\n"
        "Use FAR/DFARS/CAS/Agency supplements found in the provided text to justify.\n"
    )
    excerpt = doc["text"]
    if len(excerpt) > 8000:
        excerpt = excerpt[:8000]
    return (
        f"{preface}\n"
        f"Document: {doc['title']} | Section: {doc['section']} | URL: {doc.get('url','')}\n\n"
        f"TEXT START\n{excerpt}\nTEXT END\n\n"
        f"{JSON_INSTRUCTIONS}\n"
        f"Extract up to 8 ITEMS from this text. Respond as a JSON array of item objects only."
    )

# ---------- Dry-run mock extraction (safer) ----------
EOC_KEYWORDS: Tuple[Tuple[str, str, str], ...] = (
    ("Direct Labor", "direct", r"\bdirect\s+labor\b"),
    ("Travel", "direct", r"\btravel\b"),
    ("Direct Materials", "direct", r"\bdirect\s+materials?\b"),
    ("Subcontracts", "direct", r"\bsubcontracts?\b"),
    ("G&A", "indirect", r"\bg\s*&\s*a\b|\bgeneral\s*&\s*administrative\b|\bg and a\b"),
    ("Overhead", "indirect", r"\boverhead\b|\boh\b"),
    ("Fringe", "indirect", r"\bfringe\b"),
    ("Fee", "fee", r"\bfee\b|\bprofit\b"),
)


def _grab_sentence(text: str, pattern: str, max_words: int = 25) -> str:
    try:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            return ""
        # find sentence boundaries
        start = text.rfind(".", 0, m.start()) + 1
        end = text.find(".", m.end())
        if end == -1:
            end = len(text)
        sent = text[start:end].strip()
        words = sent.split()
        return " ".join(words[:max_words])
    except Exception:
        return ""


def make_mock_items_from_text(doc: dict) -> List[dict]:
    text = doc.get("text", "")
    items: List[dict] = []
    for name, cls, pattern in EOC_KEYWORDS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            quote = _grab_sentence(text, pattern, 22) or " ".join(text.split()[:22])
            items.append({
                "element": name,
                "classification": cls,
                "rfp_relevance": f"{name} treated as {cls} in RFP cost structure when applicable.",
                "regulatory_support": [
                    {
                        "reg_title": doc.get("title", ""),
                        "reg_section": doc.get("section", ""),
                        "quote": quote,
                        "url": doc.get("url", ""),
                        "confidence": 0.4,
                    }
                ],
                "notes": "dry-run heuristic"
            })
    if not items:
        items = [{
            "element": "Unspecified Cost Element",
            "classification": "ambiguous",
            "rfp_relevance": "Text does not clearly specify EoC; mark as ambiguous for review.",
            "regulatory_support": [{
                "reg_title": doc.get("title", ""),
                "reg_section": doc.get("section", ""),
                "quote": " ".join(text.split()[:18]),
                "url": doc.get("url", ""),
                "confidence": 0.2
            }],
            "notes": "dry-run placeholder"
        }]
    return items

# ---------- LLM call + JSON parse ----------

def call_gemini(prompt: str, *, model_name: str, max_tokens: int = 2000, temperature: float = 0.2,
                top_p: float = 0.9, retries: int = 3, dry_run: bool = False, doc: dict | None = None) -> str:
    if dry_run and doc is not None:
        return json.dumps(make_mock_items_from_text(doc), ensure_ascii=False)

    if genai is None:
        raise RuntimeError("google-generativeai SDK not available; run with --dry-run or install the SDK.")

    for i in range(retries):
        try:
            model = genai.GenerativeModel(model_name)
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
            sleep(1.2)
    raise RuntimeError("Gemini call failed after retries.")


def parse_json_array(raw_text: str) -> List[dict]:
    start = raw_text.find("[")
    end = raw_text.rfind("]") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON array found in model output.")
    blob = raw_text[start:end]
    return json.loads(blob)

# ---------- Validation & cleaning ----------

def _quote_within_limit(quote: str, limit: int = 25) -> bool:
    return len(quote.split()) <= limit


def _support_matches(element: str, title: str, section: str) -> bool:
    pats = ALLOWED_SUPPORT.get(element, [])
    blob = f"{title} {section}"
    return any(re.search(p, blob, flags=re.IGNORECASE) for p in pats) if pats else True


def clean_items(items: List[dict], doc: dict, strict: bool = False) -> Tuple[List[dict], List[str]]:
    """Validate regulatory support, cap quote length, fill attribution, and de-dupe."""
    cleaned: List[dict] = []
    warnings: List[str] = []
    seen: set = set()

    for it in items:
        if not isinstance(it, dict):
            continue
        element = str(it.get("element", "")).strip()
        if not element:
            continue
        classification = str(it.get("classification", "")).strip().lower()
        if classification not in ("direct", "indirect", "fee", "ambiguous"):
            classification = "ambiguous"
        rfp_rel = str(it.get("rfp_relevance", "")).strip()
        notes = str(it.get("notes", "")).strip()
        support = it.get("regulatory_support", []) or []

        fixed_support = []
        if not isinstance(support, list):
            support = []
        for sup in support:
            if not isinstance(sup, dict):
                continue
            sup["url"] = sup.get("url") or doc.get("url", "")
            sup["reg_title"] = sup.get("reg_title") or doc["title"]
            sup["reg_section"] = sup.get("reg_section") or doc["section"]
            quote = (sup.get("quote") or "").strip().replace("\n", " ")
            if not _quote_within_limit(quote):
                # hard-trim without adding words
                quote = " ".join(quote.split()[:25])
            sup["quote"] = quote
            try:
                sup["confidence"] = float(sup.get("confidence", 0.0))
            except Exception:
                sup["confidence"] = 0.0

            ok = _support_matches(element, sup["reg_title"], sup["reg_section"])
            if not ok:
                msg = f"Support mismatch: element '{element}' vs {sup['reg_title']} {sup['reg_section']}"
                warnings.append(msg)
                if strict:
                    continue  # drop mismatch entirely
                # mark low confidence and keep for analyst review
                sup["confidence"] = min(sup["confidence"], 0.25)
                sup["quote"] = sup["quote"] or "(quote pending)"
            fixed_support.append(sup)

        if strict and not fixed_support:
            warnings.append(f"Dropped item (no valid support): {element}")
            continue

        # De-dup key at the *fact* level to collapse repeats
        key = (element.lower(), classification, doc["id"], doc["section"])
        if key in seen:
            continue
        seen.add(key)

        fact_id = sha8("|".join(map(str, key)))
        rec = {
            "fact_id": fact_id,
            "element": element,
            "classification": classification,
            "rfp_relevance": rfp_rel,
            "regulatory_support": fixed_support,
            "notes": notes,
            "source": {
                "doc_id": doc["id"],
                "title": doc["title"],
                "section": doc["section"],
                "url": doc.get("url", "")
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        cleaned.append(rec)

    return cleaned, warnings

# ---------- CLI ----------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ProposalOS — RFP EoC Discovery (refactor)")
    ap.add_argument("--dry-run", action="store_true", help="Simulate agent outputs without calling Gemini")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of docs processed (0 = no limit)")
    ap.add_argument("--outdir", type=str, default=os.getenv("PROPOSALOS_OUTDIR", ""), help="Output base directory")
    ap.add_argument("--strict", action="store_true", help="Drop items with mismatched regulatory support")
    ap.add_argument("--model", type=str, default=os.getenv("MODEL_NAME", "gemini-2.5-pro"), help="LLM model name")
    return ap.parse_args()

# ---------- Run pipeline ----------

def run_rfp_discovery(*, dry_run: bool, limit: int, outdir: str | None, strict: bool, model_name: str) -> Tuple[str, str]:
    # Config
    load_dotenv("LLM_MODEL_G.env")
    api_key = os.getenv("GEMINI_API_KEY")

    if not dry_run:
        if genai is None:
            raise RuntimeError("google-generativeai SDK missing; run with --dry-run or install the SDK.")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing (LLM_MODEL_G.env or env var)")
        genai.configure(api_key=api_key)

    # Output directories
    base_dir = Path(outdir) if outdir else default_base_dir()
    report_dir = base_dir / "RFP_Discovery_Reports"
    kb_dir = base_dir / "RFP_KnowledgeBase"
    for d in (base_dir, report_dir, kb_dir):
        d.mkdir(parents=True, exist_ok=True)

    docs = load_parsed_regulations()
    if limit and limit > 0:
        docs = docs[:limit]

    kb_facts: List[dict] = []
    md_sections: List[str] = []
    total_warnings: List[str] = []

    for idx, doc in enumerate(docs, start=1):
        prompt = make_prompt_rfp_discovery(doc)
        try:
            raw = call_gemini(prompt, model_name=model_name, dry_run=dry_run, doc=doc)
            items = parse_json_array(raw)
        except Exception as e:
            log.error(f"Doc '{doc['title']}' parse error: {e}")
            continue

        cleaned, warnings = clean_items(items, doc, strict=strict)
        total_warnings.extend(warnings)

        if cleaned:
            sec_lines = [f"## {doc['title']} — {doc['section']}\n"]
            for rec in cleaned:
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
                        quote = sup.get("quote", "").strip().replace("\n", " ")
                        sec_lines.append(
                            f"    - {sup.get('reg_title','')}, {sup.get('reg_section','')}: \"{quote}\" "
                            f"(conf {sup.get('confidence',0):.2f}) {sup.get('url','')}"
                        )
            md_sections.append("\n".join(sec_lines))
            kb_facts.extend(cleaned)

        log.info(f"[{idx}/{len(docs)}] Processed: {doc['title']} — {doc['section']} → {len(cleaned)} facts")

    # Write outputs
    ts = now_ts()
    md_header = (
        f"# RFP EoC Discovery Report\n"
        f"**Generated (UTC):** {datetime.utcnow().isoformat()}  \n"
        f"**Model:** {model_name}\n\n---\n"
    )
    if total_warnings:
        warn_block = "\n".join(f"- {w}" for w in total_warnings)
        md_header += f"\n> Validation notes (non-fatal):\n{warn_block}\n\n---\n"

    md_body = "\n\n---\n\n".join(md_sections) if md_sections else "_No facts extracted._"
    md_path = (base_dir / "RFP_Discovery_Reports" / f"RFP_Discovery_Report_{ts}.md")
    md_path.write_text(md_header + md_body, encoding="utf-8")

    kb_path = (base_dir / "RFP_KnowledgeBase" / f"RFP_KB_Facts_{ts}.json")
    with kb_path.open("w", encoding="utf-8") as f:
        json.dump(kb_facts, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Outputs written:\n - {md_path}\n - {kb_path}")
    return str(md_path), str(kb_path)


if __name__ == "__main__":
    args = parse_args()
    try:
        run_rfp_discovery(
            dry_run=args.dry_run,
            limit=args.limit,
            outdir=args.outdir,
            strict=args.strict,
            model_name=args.model,
        )
    except Exception as e:
        log.error(f"Fatal: {e}")
        sys.exit(1)

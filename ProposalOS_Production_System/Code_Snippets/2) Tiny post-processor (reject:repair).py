import re
from typing import List, Dict, Any, Tuple

# element -> list of allowed regexes (compiled)
_ALLOWED = {
    "Travel":       [re.compile(r"^(?:31\.205-46|231\.205-46)($|[^\d])")],
    "Materials":    [re.compile(r"^31\.205-26($|[^\d])")],
    "Subcontracts": [re.compile(r"^(?:44\.\d+|15\.404-3|244\.\d+)")],  # FAR/DFARS parts supported
    "Fringe":       [re.compile(r"^31\.205-6"), re.compile(r"^415($|[^\d])")],  # CAS 415
    "Overhead":     [re.compile(r"^31\.203($|[^\d])"), re.compile(r"^418($|[^\d])")],  # CAS 418
    "G&A":          [re.compile(r"^410($|[^\d])")],  # CAS 410
    "ODC":          [re.compile(r"^31\.205-\d+")],   # must be specific, not 31.201-2
    "Fee/Profit":   [re.compile(r"^15\.404-4"), re.compile(r"^215\.404-4")],  # DFARS profit method
}

_GENERIC_ALLOWABILITY = re.compile(r"^31\.201-2($|[^\d])")

def _word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s or ""))

def _is_allowed(element: str, family: str, section: str) -> bool:
    section = (section or "").strip()
    if not section:
        return False
    # Normalize common prefixes for CAS/DFARS/FAR
    if family.upper() == "CAS":
        section = re.sub(r"^CAS[\s-]*", "", section, flags=re.I)
    if family.upper() == "DFARS" and re.match(r"^\d", section):
        section = f"2{section}" if not section.startswith("2") else section
    patterns = _ALLOWED.get(element, [])
    return any(pat.search(section) for pat in patterns)

def _repair_if_generic(fact: Dict[str, Any]) -> Dict[str, Any]:
    reg = fact.get("regulation", {}) or {}
    fam = (reg.get("family") or "").upper()
    sec = (reg.get("section") or "").strip()
    if fam == "FAR" and _GENERIC_ALLOWABILITY.match(sec):
        fact["classification"] = "ambiguous"
        fact["element"] = "Ambiguous"
        fact["ambiguity_reason"] = "Only FAR 31.201-2 (general allowability) cited; element-specific regulation required."
    return fact

def _dedupe_key(f: Dict[str, Any]) -> Tuple:
    reg = f.get("regulation", {}) or {}
    return (
        f.get("element"),
        f.get("classification"),
        reg.get("family"),
        reg.get("section"),
        (f.get("citation_text") or "").strip().lower(),
    )

def validate_and_repair_facts(facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []
    seen = set()
    for f in facts or []:
        # Quote length
        if _word_count(f.get("citation_text") or "") > 25:
            continue
        # Minimal fields
        if not f.get("element") or not f.get("classification") or not f.get("regulation"):
            continue
        # Attempt repair for generic allowability
        f = _repair_if_generic(f)

        # Allowed regs (skip if element is Ambiguous)
        if f.get("element") != "Ambiguous":
            reg = f.get("regulation") or {}
            if not _is_allowed(f["element"], reg.get("family", ""), reg.get("section", "")):
                # If ODC with a generic FAR section, downgrade to Ambiguous
                if f["element"] == "ODC" and _GENERIC_ALLOWABILITY.match((reg.get("section") or "")):
                    f["element"] = "Ambiguous"
                    f["classification"] = "ambiguous"
                    f["ambiguity_reason"] = "ODC requires a specific 31.205-x section."
                else:
                    continue  # reject

        key = _dedupe_key(f)
        if key in seen:
            continue
        seen.add(key)

        # Confidence floor (optional; keep if you already gate elsewhere)
        conf = f.get("confidence", 0.0) or 0.0
        if conf < 0.70 and f.get("element") != "Ambiguous":
            # keep ambiguous low-conf; tighten others
            continue

        cleaned.append(f)
    return cleaned

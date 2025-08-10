import re
import logging
from collections import defaultdict

# Configurable parameters
CONFIDENCE_THRESHOLD = 0.7
EXPECTED_PATTERNS = {
    "Travel": [r"31\.205-46", r"231\.205-46", r"Travel Costs"],
    "G&A": [r"CAS\s*410", r"410\.50", r"Cost Accounting Standards", r"CAS\s*418"],
    "Direct Labor": [r"31\.202", r"31\.203", r"Direct\s+costs", r"labor"],
    "Direct Materials": [r"31\.202", r"Direct\s+materials"],
    "Overhead": [r"31\.203", r"CAS\s*418", r"indirect\s+costs"],
    "Fringe": [r"31\.205-6", r"compensation", r"fringe"],
    "Fee": [r"15\.404-4", r"profit", r"Weighted\s+Guidelines"]
}

# Severity mapping based on element importance
SEVERITY_LEVELS = {
    "critical": ["Travel", "G&A"],
    "moderate": ["Direct Labor", "Direct Materials"],
    "minor": ["Overhead", "Fringe", "Fee"]
}

def validate_facts(facts):
    warnings = []
    inconsistencies = []
    element_classifications = defaultdict(set)

    for fact in facts:
        element = fact.get("element", "").strip()
        classification = fact.get("classification", "").strip().lower()
        confidence = fact.get("confidence", 0.0)

        # Track classifications for cross-regulation consistency check
        element_classifications[element].add(classification)

        # Confidence threshold check
        if confidence < CONFIDENCE_THRESHOLD:
            warnings.append(f"Low confidence ({confidence:.2f}) for {element} in section {fact.get('source', {}).get('section', '')}")

        # Citation regex check with expanded patterns
        patterns = EXPECTED_PATTERNS.get(element, [])
        for sup in fact.get("regulatory_support", []):
            title = sup.get("reg_title", "")
            section = sup.get("reg_section", "")
            blob = f"{title} {section}"
            if not any(re.search(p, blob, flags=re.IGNORECASE) for p in patterns):
                severity = next((k for k, v in SEVERITY_LEVELS.items() if element in v), "minor")
                warnings.append(f"[{severity.upper()}] Citation mismatch for {element}: expected {patterns}, got {blob}")

    # Cross-regulation consistency check
    for element, classes in element_classifications.items():
        if len(classes) > 1:
            inconsistencies.append(f"Inconsistent classifications for {element}: {', '.join(classes)}")

    return warnings, inconsistencies

# Example usage:
# facts = load_facts_from_kb_json()
# warnings, inconsistencies = validate_facts(facts)
# for w in warnings: logging.warning(w)
# for i in inconsistencies: logging.error(i)

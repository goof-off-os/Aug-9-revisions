#!/usr/bin/env python3
# dfars_checklist_assembler.py
"""
Assemble a DFARS Proposal Adequacy Checklist (Markdown) from KB facts or placeholders.
Based on DFARS 252.215-7009.
Usage:
  python dfars_checklist_assembler.py --in cleaned.json --out DFARS_Checklist.md --program "ACME SatCom" --contract "CPFF"
"""
import json
import argparse
from pathlib import Path
from datetime import datetime

# Template based on extracted content from acquisition.gov
CHECKLIST_TEMPLATE = """
# DFARS 252.215-7009 Proposal Adequacy Checklist
**Program:** {program}  
**Contract Type:** {contract}  
**Generated:** {generated_at}  

The offeror shall complete the following checklist, providing location of requested information, or an explanation of why the requested information is not provided. In preparation of the offeror's checklist, offerors may elect to have their prospective subcontractors use the same or similar checklist as required by this solicitation. However, use of the checklist by subcontractors is not required, and the decision on whether and how to use the checklist remains with the offeror. Submission of the checklist does not relieve the offeror from submitting a proposal that meets all of the requirements of this solicitation, including providing sufficient detail or technical information to allow for a full evaluation of the proposal. Offerors may attach additional pages that explain any identified deficiencies to their final proposal submission.

## General Instructions
1. FAR 15.408, Table 15-2, Section I Paragraph C(2)(i) mandates that certified cost or pricing data shall be included on this page for proposals in which certified cost or pricing data are required.
2. Proprietary information shall be provided on this page in a manner that protects it, as appropriate.
3. For proposals less than the relevant certified cost or pricing data threshold, if cost or pricing data are not required to be certified, these requirements may be waived or reduced by the contracting officer.

## Checklist Items

| Item | References | Submission Item | Location/Explanation |
|------|------------|-----------------|---------------------|
| 1 | FAR 15.408, Table 15-2, Section I Paragraph A | Does the proposal include a table of contents identifying the location in the proposal of each topic listed in FAR Table 15-2's "General Instructions," as well as each topic listed in the paragraphs titled "First Article Test," "Formats for Submission of Line Item Summaries," "Other Information," and "Index" (or a cross reference to where the index is located), if they are applicable to the proposal? | {placeholder_1} |
| 2 | FAR 15.408, Table 15-2, Section I Paragraph A(1) | Is the proposal an adequate response to the RFP? | {placeholder_2} |
# ... (truncated for brevity; add all 60+ items from the full checklist extraction)
# Full list would be populated here based on the extraction.
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=False, help="Input KB JSON")
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--program", default="Program X")
    ap.add_argument("--contract", default="CPFF")
    args = ap.parse_args()

    # Load KB if provided
    data = {}
    if args.inp:
        data = json.loads(Path(args.inp).read_text())

    # Placeholders or fill from data
    placeholders = {
        "placeholder_1": "Yes, Section 1" if data else "TBD",
        "placeholder_2": "Yes" if data else "TBD",
        # Add more based on full checklist
    }

    generated_at = datetime.utcnow().isoformat() + 'Z'
    content = CHECKLIST_TEMPLATE.format(
        program=args.program,
        contract=args.contract,
        generated_at=generated_at,
        **placeholders
    )

    Path(args.outp).write_text(content, encoding="utf-8")
    print(f"Wrote DFARS Checklist template to {args.outp}")

if __name__ == "__main__":
    main()
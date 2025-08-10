#!/usr/bin/env python3
# dfars_cover_page_assembler.py
"""
Assemble DFARS Cost Volume Cover Page (Markdown) based on SF1411.
Usage:
  python dfars_cover_page_assembler.py --out DFARS_Cover_Page.md --program "ACME SatCom"
"""
import argparse
from pathlib import Path
from datetime import datetime

COVER_PAGE_TEMPLATE = """
# Contract Pricing Proposal Cover Sheet (SF 1411 Equivalent)
**Program:** {program}  
**Generated:** {generated_at}  

1. SOLICITATION/CONTRACT/MODIFICATION NUMBER: {placeholder_1}  
2. NAME OF OFFEROR: {placeholder_2}  
   a. First Line Address:  
   c. Street Address:  
   d. City:  
   e. State:  
   f. Zip Code:  
3. NAME OF OFFEROR'S POINT OF CONTACT:  
   a. Name:  
   b. Title:  
   c. Telephone Area Code Number:  
4. TYPE OF CONTRACT ACTION: [ ] NEW CONTRACT [ ] CHANGE ORDER ...  
... (full fields from extraction)
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--program", default="Program X")
    args = ap.parse_args()

    generated_at = datetime.utcnow().isoformat() + 'Z'
    content = COVER_PAGE_TEMPLATE.format(
        program=args.program,
        generated_at=generated_at,
    )

    Path(args.outp).write_text(content, encoding="utf-8")
    print(f"Wrote DFARS Cover Page template to {args.outp}")

if __name__ == "__main__":
    main()
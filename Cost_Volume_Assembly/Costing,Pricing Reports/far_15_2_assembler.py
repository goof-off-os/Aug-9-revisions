#!/usr/bin/env python3
# far_15_2_assembler.py
"""
Assemble FAR 15.408 Table 15-2 Proposal Guide (Markdown) with placeholders.
Usage:
  python far_15_2_assembler.py --out FAR_15-2.md --program "ACME SatCom"
"""
import argparse
from pathlib import Path
from datetime import datetime

# Template based on extracted FAR Table 15-2 content
FAR_15_2_TEMPLATE = """
# FAR 15.408 Table 15-2 - Instructions for Submitting Cost/Price Proposals
**Program:** {program}  
**Generated:** {generated_at}  

## I. General Instructions
A. You must provide the following information on the first page of your pricing proposal:
1. Solicitation, contract, and/or modification number;  
2. Name and address of offeror;  
3. Name and telephone number of point of contact;  
... (full list from extraction)

## II. Cost Elements
Depending on your system, you must provide breakdowns for the following basic cost elements, as applicable:  
1. Materials and services. Provide a consolidated priced summary of individual material quantities...  
{placeholders for cost elements from KB}

## III. Formats for Submission of Line Item Summaries
A. New Contracts (Including Letter Contracts)...  
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--program", default="Program X")
    args = ap.parse_args()

    generated_at = datetime.utcnow().isoformat() + 'Z'
    content = FAR_15_2_TEMPLATE.format(
        program=args.program,
        generated_at=generated_at,
    )

    Path(args.outp).write_text(content, encoding="utf-8")
    print(f"Wrote FAR 15-2 template to {args.outp}")

if __name__ == "__main__":
    main()
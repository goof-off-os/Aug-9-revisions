#!/usr/bin/env python3
# fccom_form_assembler.py
"""
Assemble FCCOM (DD Form 1861) Markdown template.
Usage:
  python fccom_form_assembler.py --out FCCOM_Form.md --program "ACME SatCom"
"""
import argparse
from pathlib import Path
from datetime import datetime

FCCOM_TEMPLATE = """
# Facilities Capital Cost of Money (FCCOM) - DD Form 1861
**Program:** {program}  
**Generated:** {generated_at}  

## Form Fields
1. CONTRACTOR NAME: {placeholder_name}  
2. CONTRACTOR ADDRESS: {placeholder_address}  
3. BUSINESS UNIT: {placeholder_unit}  
4. RFP/CONTRACT PIIN NUMBER: {placeholder_piin}  
5. PERFORMANCE PERIOD: {placeholder_period}  

## 6. DISTRIBUTION OF FACILITIES CAPITAL COST OF MONEY POOL
- a. ALLOCATION BASE: {placeholder_base}  
- b. AMOUNT: {placeholder_amount}  
- c. FACTOR (1) AMOUNT: {placeholder_factor_amount} (2) PERCENTAGE: {placeholder_factor_pct}  
- d. TOTAL CONTRACT FACILITIES CAPITAL COST OF MONEY: {placeholder_total}  
- e. TREASURY RATE: {placeholder_rate}  
- f. FACILITIES CAPITAL EMPLOYED: {placeholder_employed} (Total / Treasury Rate)  

## 7. DISTRIBUTION OF FACILITIES CAPITAL EMPLOYED
- (1) LAND: {placeholder_land}%  
- (2) BUILDINGS: {placeholder_buildings}%  
- (3) EQUIPMENT: {placeholder_equipment}%  
- (4) TOTAL: 100%  
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--program", default="Program X")
    args = ap.parse_args()

    placeholders = {
        "placeholder_name": "TBD",
        # Add more
    }

    generated_at = datetime.utcnow().isoformat() + 'Z'
    content = FCCOM_TEMPLATE.format(
        program=args.program,
        generated_at=generated_at,
        **placeholders
    )

    Path(args.outp).write_text(content, encoding="utf-8")
    print(f"Wrote FCCOM Form template to {args.outp}")

if __name__ == "__main__":
    main()
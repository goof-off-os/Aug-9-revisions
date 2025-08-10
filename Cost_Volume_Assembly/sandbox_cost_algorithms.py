
#!/usr/bin/env python3
# sandbox_cost_algorithms.py
"""
Lightweight cost algorithms for ProposalOS Cost Volume assembly.
- Deterministic math (no LLM calls)
- Produces pandas DataFrames for markdown rendering
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import math
import pandas as pd

@dataclass
class LaborLine:
    wbs: str
    labor_cat: str
    hours: float
    base_rate: float        # current year $/hr
    location: str = ""

@dataclass
class RateSet:
    fringe: float           # e.g., 0.28 = 28%
    overhead: float         # OH on direct labor, e.g., 0.75
    gna: float              # G&A on total cost input base, e.g., 0.12
    escalation: float = 0.0 # annual escalation, simple compounding

@dataclass
class TravelLine:
    wbs: str
    trips: int
    airfare: float
    lodging_nights: int
    lodging_rate: float
    perdiem_days: int
    perdiem_rate: float
    local_miles: float = 0.0
    mileage_rate: float = 0.0

@dataclass
class MaterialLine:
    wbs: str
    part_no: str
    qty: int
    unit_price: float
    material_handling: float = 0.0  # handling burden percent on materials
    scrap: float = 0.0              # scrap factor percent

@dataclass
class SubcontractLine:
    wbs: str
    vendor: str
    cost: float
    handling: float = 0.0           # optional handling burden
    fee_excluded_from_base: bool = False

# ---------- Helpers ----------
def escalate(rate: float, years: float, annual_escalation: float) -> float:
    return rate * ((1 + annual_escalation) ** years)

def to_markdown(df: pd.DataFrame) -> str:
    # Safe markdown with 2 decimal places where numeric
    fmt = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            fmt[col] = "{:,.2f}".format
    return df.to_markdown(index=False, floatfmt=".2f")

# ---------- Labor ----------
def build_labor_table(lines: List[LaborLine], rates: RateSet, years_from_base: float = 0.0) -> Tuple[pd.DataFrame, Dict[str, float]]:
    rows = []
    for ln in lines:
        rate_esc = escalate(ln.base_rate, years_from_base, rates.escalation)
        direct = ln.hours * rate_esc
        fringe = direct * rates.fringe
        oh = (direct + fringe) * rates.overhead  # OH applied after fringe
        burdened = direct + fringe + oh
        rows.append({
            "WBS": ln.wbs,
            "Labor Cat": ln.labor_cat,
            "Hours": ln.hours,
            "Base Rate": ln.base_rate,
            "Esc Rate": rate_esc,
            "Direct $": direct,
            "Fringe $": fringe,
            "Overhead $": oh,
            "Burdened Labor $": burdened
        })
    df = pd.DataFrame(rows)
    totals = {
        "direct": float(df["Direct $"].sum()) if len(df)>0 else 0.0,
        "fringe": float(df["Fringe $"].sum()) if len(df)>0 else 0.0,
        "overhead": float(df["Overhead $"].sum()) if len(df)>0 else 0.0,
        "burdened_labor": float(df["Burdened Labor $"].sum()) if len(df)>0 else 0.0,
    }
    return df, totals

# ---------- Materials ----------
def build_materials_table(lines: List[MaterialLine]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    rows = []
    for ln in lines:
        gross = ln.qty * ln.unit_price
        scrap_cost = gross * ln.scrap
        handling = (gross + scrap_cost) * ln.material_handling
        total = gross + scrap_cost + handling
        rows.append({
            "WBS": ln.wbs,
            "Part": ln.part_no,
            "Qty": ln.qty,
            "Unit $": ln.unit_price,
            "Gross $": gross,
            "Scrap $": scrap_cost,
            "Handling $": handling,
            "Total Material $": total
        })
    df = pd.DataFrame(rows)
    totals = {
        "gross": float(df["Gross $"].sum()) if len(df)>0 else 0.0,
        "scrap": float(df["Scrap $"].sum()) if len(df)>0 else 0.0,
        "handling": float(df["Handling $"].sum()) if len(df)>0 else 0.0,
        "total_material": float(df["Total Material $"].sum()) if len(df)>0 else 0.0,
    }
    return df, totals

# ---------- Subcontracts ----------
def build_subcontracts_table(lines: List[SubcontractLine]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    rows = []
    for ln in lines:
        handling = ln.cost * ln.handling
        total = ln.cost + handling
        rows.append({
            "WBS": ln.wbs,
            "Vendor": ln.vendor,
            "Cost $": ln.cost,
            "Handling $": handling,
            "Total SubK $": total,
            "Fee Excl. Base": "Yes" if ln.fee_excluded_from_base else "No"
        })
    df = pd.DataFrame(rows)
    totals = {
        "cost": float(df["Cost $"].sum()) if len(df)>0 else 0.0,
        "handling": float(df["Handling $"].sum()) if len(df)>0 else 0.0,
        "total_subk": float(df["Total SubK $"].sum()) if len(df)>0 else 0.0,
        "fee_excl_base_amount": float(df.loc[df["Fee Excl. Base"]=="Yes","Total SubK $"].sum()) if len(df)>0 else 0.0,
    }
    return df, totals

# ---------- Travel ----------
def build_travel_table(lines: List[TravelLine]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    rows = []
    for ln in lines:
        airfare = ln.trips * ln.airfare
        lodging = ln.lodging_nights * ln.lodging_rate
        perdiem = ln.perdiem_days * ln.perdiem_rate
        mileage = ln.local_miles * ln.mileage_rate
        total = airfare + lodging + perdiem + mileage
        rows.append({
            "WBS": ln.wbs,
            "Trips": ln.trips,
            "Airfare $": airfare,
            "Lodging $": lodging,
            "Per Diem $": perdiem,
            "Mileage $": mileage,
            "Total Travel $": total
        })
    df = pd.DataFrame(rows)
    totals = {
        "airfare": float(df["Airfare $"].sum()) if len(df)>0 else 0.0,
        "lodging": float(df["Lodging $"].sum()) if len(df)>0 else 0.0,
        "perdiem": float(df["Per Diem $"].sum()) if len(df)>0 else 0.0,
        "mileage": float(df["Mileage $"].sum()) if len(df)>0 else 0.0,
        "total_travel": float(df["Total Travel $"].sum()) if len(df)>0 else 0.0,
    }
    return df, totals

# ---------- G&A Base + Fee ----------
def compute_bases_and_fee(labor_totals, mat_totals, subk_totals, travel_totals, rates: RateSet, fee_pct: float, exclude_subk_from_fee: bool = False) -> Dict[str, float]:
    # Cost input base for G&A: burdened labor + total material + total subk + total travel
    base_gna = labor_totals["burdened_labor"] + mat_totals["total_material"] + subk_totals["total_subk"] + travel_totals["total_travel"]
    gna_amt = base_gna * rates.gna

    # Fee base: by default same as total cost excluding G&A, optionally exclude subcontracts
    fee_base = labor_totals["burdened_labor"] + mat_totals["total_material"] + travel_totals["total_travel"]
    if not exclude_subk_from_fee:
        fee_base += subk_totals["total_subk"]
    fee_amt = fee_base * fee_pct

    grand_total = base_gna + gna_amt + fee_amt  # base includes all pre-G&A costs
    return {
        "base_gna": base_gna,
        "gna_amt": gna_amt,
        "fee_base": fee_base,
        "fee_amt": fee_amt,
        "grand_total": grand_total
    }

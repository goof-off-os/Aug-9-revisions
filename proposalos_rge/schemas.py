# proposalos_rge/schemas.py
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# --- Core sub-objects -------------------------------------------------------
class RegulatorySupport(BaseModel):
    reg_title: str = ""
    reg_section: str = ""
    quote: str = ""
    url: str = ""
    confidence: float = 0.0
    validated: Optional[bool] = None

class SourceRef(BaseModel):
    doc_id: Optional[str] = None
    title: Optional[str] = None
    section: Optional[str] = None
    url: Optional[str] = None

class KBFact(BaseModel):
    fact_id: Optional[str] = None
    element: str
    classification: Literal["direct", "indirect", "fee", "ambiguous"] = "ambiguous"
    rfp_relevance: Optional[str] = None
    regulatory_support: List[RegulatorySupport] = Field(default_factory=list)
    notes: Optional[str] = None
    source: Optional[SourceRef] = None
    timestamp: Optional[str] = None
    # Some of your KB entries also include top-level confidence
    confidence: Optional[float] = None

class Allocation(BaseModel):
    fy: str                      # e.g., "FY2026"
    clin: Optional[str] = None
    wbs: Optional[str] = None
    task: Optional[str] = None
    ipt: Optional[str] = None
    hours: float = 0.0
    rate: Optional[float] = None
    cost: Optional[float] = None

class Assumption(BaseModel):
    text: str
    source: Optional[str] = None

class HEF(BaseModel):
    basis_year: int
    series: Dict[str, float]      # e.g., {"FY2024":1.00, "FY2025":1.03, ...}

class GFX(BaseModel):
    type: Literal["GFE", "GFX"]
    description: str
    provided_by: Optional[str] = None

class ChartSpec(BaseModel):
    id: str
    title: str
    series: List[Dict]            # renderer-agnostic; e.g., [{"x":"fy","y":"cost","group":"element"}]
    filters: Dict[str, str] = {}

class UIInputs(BaseModel):
    mode: Optional[str] = None
    level: Optional[str] = None               # CLIN/WBS/BOE/Task/IPT/Total
    fee_method: Optional[str] = None          # e.g., "target_percent"
    fee_value: Optional[float] = None
    contract_type: Optional[str] = None       # CPFF, FFP, etc.
    prime_or_sub: Optional[str] = None        # prime|sub
    customer_id: Optional[str] = None
    fiscal_years: List[str] = []

class RFPMeta(BaseModel):
    rfp_id: Optional[str] = None
    title: Optional[str] = None
    customer: Optional[str] = None
    url: Optional[str] = None

class AuditEntry(BaseModel):
    kind: Literal["warning", "error", "info"] = "info"
    code: str
    message: str
    context: Dict[str, str] = {}

class Audit(BaseModel):
    validations: List[AuditEntry] = Field(default_factory=list)
    conflicts: List[AuditEntry] = Field(default_factory=list)

# --- Unified Payload --------------------------------------------------------
class UnifiedPayload(BaseModel):
    ui: UIInputs
    rfp: Optional[RFPMeta] = None
    facts: List[KBFact] = Field(default_factory=list)
    allocations: List[Allocation] = Field(default_factory=list)
    assumptions: List[Assumption] = Field(default_factory=list)
    hefs: List[HEF] = Field(default_factory=list)
    gfx: List[GFX] = Field(default_factory=list)
    chart_specs: List[ChartSpec] = Field(default_factory=list)
    audit: Audit = Field(default_factory=Audit)
    generated_at_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat()+"Z")
# ProposalOS — Report Generation Engine (RGE) MVP

This drops in alongside your current repo and **wraps the existing assemblers** as renderers. It gives you:

- **Unified Payload** (`schemas.py`)
- **Template Registry** (`registry.py`)
- **Markdown Renderer (Annual FY)** refactor that replaces `annual_fiscal_year_report_assembler.py` CLI usage
- **FastAPI Endpoints** (`api/endpoints.py`) for `/reports/preview`, `/reports/generate`, `/reports/validate`, `/reports/templates`
- **Glue** to load `KB_cleaned.json` and to reuse your current validation rules from `compile_reports_refactor (1).py`

> Minimal external deps: `pydantic`, `fastapi`, `jinja2` (optional), and your existing stack.

---

## Package layout

```
proposalos_rge/
  __init__.py
  schemas.py
  registry.py
  inputs/
    kb_loader.py
    ui_adapter.py
  normalize/
    builder.py
  validate/
    rules.py
  render/
    __init__.py
    md/
      annual_fy.py
  api/
    endpoints.py
```

---

## `schemas.py` — Unified Payload models (Pydantic)

```python
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
```

````

---

## `registry.py` — Template registry (MVP 3 entries)
```python
# proposalos_rge/registry.py
from typing import Dict, List, TypedDict

class SectionSpec(TypedDict, total=False):
    id: str
    renderer: str  # dotted path, e.g., "proposalos_rge.render.md.annual_fy:render"
    title: str
    required_fields: List[str]

class TemplateSpec(TypedDict, total=False):
    name: str
    description: str
    sections: List[SectionSpec]

REGISTRY: Dict[str, TemplateSpec] = {
    "ANNUAL_FY": {
        "name": "Annual Fiscal Year Rollup",
        "description": "Per-FY cost rollups at selected level.",
        "sections": [
            {
                "id": "annual_fy_core",
                "title": "Annual FY Rollup",
                "renderer": "proposalos_rge.render.md.annual_fy:render",
                "required_fields": ["allocations"]
            }
        ]
    },
    "DFARS_CHECKLIST": {
        "name": "DFARS 252.215-7009 Checklist",
        "description": "Checklist table populated from payload facts (TBD).",
        "sections": []
    },
    "DFARS_COVER_PAGE": {
        "name": "DFARS Cover Page (SF1411-like)",
        "description": "Cover sheet scaffold (TBD).",
        "sections": []
    }
}
````

---

## `inputs/kb_loader.py` — Load KB JSON and adapt to `UnifiedPayload.facts`

```python
# proposalos_rge/inputs/kb_loader.py
from pathlib import Path
import json
from typing import List
from ..schemas import KBFact, UnifiedPayload, UIInputs


def load_kb_to_payload(kb_path: str, ui: UIInputs) -> UnifiedPayload:
    data = json.loads(Path(kb_path).read_text())
    facts = [KBFact(**f) for f in data.get("facts", [])]
    return UnifiedPayload(ui=ui, facts=facts)
```

---

## `normalize/builder.py` — (MVP) pass-through builder + future merge hooks

```python
# proposalos_rge/normalize/builder.py
from ..schemas import UnifiedPayload, UIInputs


def build_unified_payload(ui: UIInputs, base_payload: UnifiedPayload) -> UnifiedPayload:
    """For MVP: return provided payload; later merge UI + RFP + KB here."""
    payload = base_payload.copy(deep=True)
    payload.ui = ui
    return payload
```

---

## `validate/rules.py` — Reuse your existing validator

```python
# proposalos_rge/validate/rules.py
from typing import Tuple, List
from ..schemas import UnifiedPayload, AuditEntry

# We will import your existing function; rename file if needed to avoid spaces
try:
    # If you rename to compile_reports_refactor.py this works directly
    from compile_reports_refactor import validate_facts  # type: ignore
except Exception:
    # Fallback: import via the current filename with space/paren using importlib
    import importlib.util, sys, pathlib
    p = pathlib.Path(__file__).resolve().parent.parent.parent / "compile_reports_refactor (1).py"
    spec = importlib.util.spec_from_file_location("_crr_mod", str(p))
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)                 # type: ignore
    validate_facts = getattr(mod, "validate_facts")


def run_validators(payload: UnifiedPayload) -> UnifiedPayload:
    warnings, inconsistencies = validate_facts([f.dict() for f in payload.facts])
    for w in warnings:
        payload.audit.validations.append(AuditEntry(kind="warning", code="validator", message=w))
    for i in inconsistencies:
        payload.audit.validations.append(AuditEntry(kind="error", code="consistency", message=i))
    return payload
```

---

## `render/md/annual_fy.py` — Refactor of `annual_fiscal_year_report_assembler.py`

```python
# proposalos_rge/render/md/annual_fy.py
from collections import defaultdict
from datetime import datetime
from ...schemas import UnifiedPayload


def _infer_allocations_from_facts(payload: UnifiedPayload):
    """MVP shim: if caller didn't provide allocations, create a toy rollup
    by counting fact elements per FY (placeholder logic). Replace with your
    real CLIN/WBS rollup once available.
    """
    if payload.allocations:
        return payload.allocations

    # naive placeholder: one $1,000 per fact to FY of ui.fiscal_years[0]
    fy = (payload.ui.fiscal_years or ["FY2025"])[0]
    from ...schemas import Allocation
    allocs = []
    for fact in payload.facts:
        allocs.append(Allocation(fy=fy, task=fact.element, hours=0.0, cost=1000.0))
    return allocs


def render(payload: UnifiedPayload) -> str:
    allocs = payload.allocations or _infer_allocations_from_facts(payload)
    # aggregate
    by_fy = defaultdict(lambda: defaultdict(float))
    level = (payload.ui.level or "Total").lower()

    for a in allocs:
        key = {
            "resource": a.task or a.wbs or a.clin or "Resource",
            "task": a.task or "Task",
            "clin": a.clin or "CLIN",
            "wbs": a.wbs or "WBS",
            "ipt": a.ipt or "IPT",
            "total": "Total"
        }.get(level, "Total")
        by_fy[a.fy][key] += (a.cost or 0.0)

    lines = [f"# Annual Fiscal Year Report",
             f"**Level:** {payload.ui.level or 'Total'}  ",
             f"**Generated (UTC):** {datetime.utcnow().isoformat()}Z\n"]

    for fy, bucket in by_fy.items():
        lines.append(f"## {fy}")
        for k, total in sorted(bucket.items()):
            lines.append(f"- {k}: ${total:,.2f}")
    return "\n".join(lines) + "\n"
```

---

## `api/endpoints.py` — Minimal FastAPI over the engine

```python
# proposalos_rge/api/endpoints.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from importlib import import_module
from typing import Optional, Dict, Any

from ..schemas import UnifiedPayload, UIInputs
from ..registry import REGISTRY
from ..inputs.kb_loader import load_kb_to_payload
from ..normalize.builder import build_unified_payload
from ..validate.rules import run_validators

router = APIRouter(prefix="/reports", tags=["reports"])

class PreviewBody(BaseModel):
    ui: UIInputs
    kb_path: Optional[str] = None
    payload: Optional[UnifiedPayload] = None
    template: str = "ANNUAL_FY"

class GenerateBody(PreviewBody):
    export: Optional[Dict[str, Any]] = {}

@router.get("/templates")
def list_templates():
    return {"templates": REGISTRY}

@router.post("/validate")
def validate_only(body: PreviewBody):
    if not (body.payload or body.kb_path):
        raise HTTPException(400, "Provide either payload or kb_path")
    payload = body.payload or load_kb_to_payload(body.kb_path, body.ui)
    payload = build_unified_payload(body.ui, payload)
    payload = run_validators(payload)
    return payload.dict()

@router.post("/preview")
def preview(body: PreviewBody):
    if body.template not in REGISTRY:
        raise HTTPException(404, f"Unknown template {body.template}")

    payload = body.payload or load_kb_to_payload(body.kb_path, body.ui)
    payload = build_unified_payload(body.ui, payload)
    payload = run_validators(payload)

    rendered_sections = []
    for sec in REGISTRY[body.template]["sections"]:
        mod_path, fn_name = sec["renderer"].split(":")
        fn = getattr(import_module(mod_path), fn_name)
        rendered_sections.append({"id": sec["id"], "title": sec.get("title",""), "markdown": fn(payload)})

    return {"audit": payload.audit.dict(), "sections": rendered_sections}

@router.post("/generate")
def generate(body: GenerateBody):
    # For MVP, same as preview; wire PDF/Docx exporters here later
    return preview(body)
```

---

## How to wire this into your **orchestrator**

```python
# orchestrator_enhanced.py (snippet)
from proposalos_rge.api.endpoints import router as rge_router
app.include_router(rge_router)
```

---

## Quick smoke test (local)

```bash
uvicorn proposalos_rge.api.endpoints:router --factory
# or run within your FastAPI main and hit:
# POST /reports/preview with body:
# {
#   "ui": {"level":"Resource", "fiscal_years":["FY2026"]},
#   "kb_path": "/mnt/data/KB_cleaned.json",
#   "template": "ANNUAL_FY"
# }
```

---

### Notes & next steps

- **Conflict Manager**: add a small helper that compares `ui.contract_type` vs any RFP/KB detected contract types and pushes an `audit.conflicts[]` entry instead of overwriting.
- **More renderers**: move `dfars_checklist_assembler.py` and `dfars_cover_page_assembler.py` bodies into `render/md/dfars_checklist.py` and `render/md/dfars_cover.py`; register them.
- **Allocations**: swap the placeholder in `annual_fy` with your real CLIN/WBS/FY rollups as soon as those structures are available in the payload.
- **Validators**: your `compile_reports_refactor (1).py` already returns warnings/inconsistencies. Consider adding math ties and citation-length checks here as separate functions.


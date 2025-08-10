Refactor plan (structure, naming, patterns)
Goals

Single, obvious entry points; no duplicate scripts.

Central config/secrets; zero hardcoded URLs/keys/models.

Consistent I/O schemas (pydantic), typed code, and clear error paths.

Safe external calls (timeouts, retries, circuit breakers).

Testable seams (pure functions; adapters at the edges).

New repo layout

bash
Copy
Edit
proposalos/
  apps/
    orchestrator/                # FastAPI service (stateful interrogation + validation)
      __init__.py
      main.py
      config.py
      security.py
      rate_limit.py
      models.py
      routes/
        orchestrate.py
        validate_boe.py
        sessions.py
    reporting/                   # Reporting engine (BigQuery/GCS / PDFs)
      __init__.py
      main.py
      generators/
        compliance_audit.py
  services/
    rfp_eoc_discovery/           # (renamed from complile_reports.py)
      __init__.py
      discovery.py
      prompts.py
      io.py                      # load_parsed_regulations, file writers
      validate.py                # regex rules, quote-length checks
  integrators/
    procurement/
      __init__.py
      procurement_integrator.py
  templates/
    render/md/                   # DFARS checklist, cover page, annual FY report
      dfars_checklist_assembler.py
      dfars_cover_page_assembler.py
      annual_fiscal_year_report_assembler.py
  shared/
    config.py                    # Env, paths, model selection, timeouts
    logging.py
    errors.py
    types.py
    http.py                      # httpx clients with retry/timeout
  tests/
    unit/
    integration/
  .env.example
  pyproject.toml
  docker/
    orchestrator.Dockerfile
    reporting.Dockerfile
  .github/workflows/ci.yml
Naming & patterns

Files: snake_case.py; packages are nouns; modules are what they are (not verbs).

Configuration via shared/config.py (pydantic‑settings); no one‑off .env filenames.

Pydantic models for every request/response + on‑disk JSON schemas.

Ports of call to the outside (LLMs, SAM.gov, GCP, Redis) go through shared/http.py or explicit adapters; never from deep business code.

“Default‑deny” security: every route behind an auth dependency; keys hashed; CORS explicit allowlist per env.

Rate limiting: Redis token bucket middleware.

Validation stage gates:

Schema validity ✅

Quote length (≤25 words) ✅

Citation regex match ✅

Confidence ≥ threshold ✅

Cross‑regulation consistency ✅

Run / setup instructions
Prereqs

Python 3.11+, Docker, Make (optional), Redis (for RL), GCP creds (if using reporting), SAM API Key (optional).

Environment

bash
Copy
Edit
cp .env.example .env
# Edit values:
# GEMINI_API_KEY=...
# GCP_PROJECT_ID=proposalos-prod
# REDIS_URL=redis://localhost:6379/0
# API_KEY_HASH=<sha256 of your API key string>
# REPORT_STORAGE_BUCKET=proposalos-reports
# SAM_API_KEY=...
Install

bash
Copy
Edit
pip install -U pip
pip install -e .  # uses pyproject.toml
pre-commit install
Run (local)

bash
Copy
Edit
# Orchestrator API (FastAPI)
uvicorn apps.orchestrator.main:app --reload --port 8000

# Reporting engine
uvicorn apps.reporting.main:app --reload --port 8080

# RFP EoC discovery (dry run)
python -m services.rfp_eoc_discovery.discovery --dry-run --limit 10
Docker (prod‑ish)

bash
Copy
Edit
docker build -f docker/orchestrator.Dockerfile -t proposalos/orchestrator:latest .
docker run --env-file .env -p 8000:8000 proposalos/orchestrator:latest
Quick security & compliance audit (what to fix now)
Secrets / API keys

✅ Load via env only; never from bespoke files like LLM_MODEL_G.env. Centralize in shared/config.py.

🔐 Hash inbound API keys server‑side and compare to API_KEY_HASH.

🔁 Rotate keys; keep short TTLs for SA tokens; use GCP Secret Manager/Vault in prod.

Network calls

httpx client with: timeout=30s, retries=3 (backoff), follow_redirects=False, and whitelist egress domains per service.

Explicit user agent & audit logging of destination, method, status, and latency.

Add circuit breaker (e.g., pybreaker) for Gemini/SAM/GCP spikes.

Data paths

Stop writing directly to ~/Desktop/.... Use XDG_STATE_HOME or an app data dir under ./var/ with per‑run subfolders; or write to GCS/S3 in prod.

Sanitize all filenames (slugify) and ensure permissions 0600.

Never echo secrets in logs; set logger to redact Authorization, api_key, token.

Compliance

LLM outputs must retain provable provenance: quote (≤25 words), section, URL, confidence score.

Enforce FAR/DFARS regex gates and confidence thresholds at the boundary (fail the run if requirements are not met).

Keep an audit JSON per run that includes inputs, model, prompts hash, and validation results.

File‑by‑file code review (with concrete fixes)
Below are surgical patches (minimal diff‑style) you can apply.

1) complile_reports.py → rename to services/rfp_eoc_discovery/discovery.py
Issues

Writes to ~/Desktop/...; brittle paths.

Hardcoded .env filename and model choice in code paths.

No schema validation for model output; quote length/regex checks are post‑hoc and partial.

Missing robust retry/timeout around Gemini.

Mixed responsibilities (I/O, prompting, validation) in one file.

Fixes (patch snippets)

a) Centralize config & paths

python
Copy
Edit
# services/rfp_eoc_discovery/io.py
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OUTPUT_DIR: Path = Path("./var/outputs")
    MODEL_NAME: str = "gemini-2.5-pro"
    CONFIDENCE_MIN: float = 0.7
    class Config: env_file = ".env"

settings = Settings()
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def out_paths(prefix: str):
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    md = settings.OUTPUT_DIR / f"{prefix}_{ts}.md"
    kb = settings.OUTPUT_DIR / f"{prefix}_{ts}.json"
    return md, kb
b) Strong JSON schema for items

python
Copy
Edit
# services/rfp_eoc_discovery/validate.py
from pydantic import BaseModel, Field, AnyUrl, conlist

class Support(BaseModel):
    reg_title: str
    reg_section: str
    quote: str = Field(min_length=1, max_length=300)
    url: AnyUrl | None = None
    confidence: float = Field(ge=0, le=1)

class Item(BaseModel):
    element: str
    classification: str
    rfp_relevance: str | None = None
    regulatory_support: conlist(Support, min_items=1)
    notes: str | None = None
c) Enforce quote length + regexes

python
Copy
Edit
QUOTE_MAX_WORDS = 25
EXPECTED = {
  "Travel": [r"\b31\.205-46\b", r"\b231\.205-46\b", r"\bGSA\b"],
  "G&A": [r"\bCAS\s*410\b", r"\b410\.50\b"]
  # ...
}

def quote_ok(q: str) -> bool:
    return len(q.strip().split()) <= QUOTE_MAX_WORDS

def citation_ok(element: str, title: str, section: str) -> bool:
    blob = f"{title} {section}"
    pats = EXPECTED.get(element, [])
    return any(re.search(p, blob, re.I) for p in pats)
d) Safer LLM call

python
Copy
Edit
# shared/http.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def post_json(url, json, headers=None, timeout=30):
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as c:
        return await c.post(url, json=json, headers=headers)
e) Stage gate before write

python
Copy
Edit
valid_items = []
for raw in items:
    obj = Item.model_validate(raw)
    if not all(quote_ok(s.quote) and citation_ok(obj.element, s.reg_title, s.reg_section)
               for s in obj.regulatory_support):
        continue
    if mean([s.confidence for s in obj.regulatory_support]) < settings.CONFIDENCE_MIN:
        continue
    valid_items.append(obj)
2) orchestrator_enhanced.py
Issues

Auth is optional when API_KEY_HASH not set → make default‑deny.

Rate limiting missing in hot path; Redis client optional but no guard rail.

Gemini/model calls without circuit breaker; extraction JSON parsing brittle.

CORS * in prod—tighten per‑env.

Session export exposes raw fields; add scrubber.

Fixes

a) Default‑deny API auth

python
Copy
Edit
# apps/orchestrator/security.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
import os, hashlib

security = HTTPBearer(auto_error=False)
API_KEY_HASH = os.getenv("API_KEY_HASH")

def require_api_key(credentials = Depends(security)):
    if not API_KEY_HASH:
        raise HTTPException(status_code=503, detail="Server not provisioned (auth)")
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing API key")
    provided = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if provided != API_KEY_HASH:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True
…and use Depends(require_api_key) on every route.

b) Redis token‑bucket

python
Copy
Edit
# apps/orchestrator/rate_limit.py
import time, math, redis
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
RATE=60; BURST=120

def allow(api_key: str)->bool:
    key=f"rl:{api_key}"
    now=time.time()
    bucket=r.hgetall(key)
    tokens=float(bucket.get("tokens", BURST))
    last=float(bucket.get("ts", now))
    tokens=min(BURST, tokens + (now-last)*RATE/60.0)
    if tokens<1: return False
    r.hset(key, mapping={"tokens": tokens-1, "ts": now})
    r.expire(key, 3600)
    return True
Middleware:

python
Copy
Edit
@app.middleware("http")
async def rl_mw(request, call_next):
    api_key = request.headers.get("Authorization","").replace("Bearer ","")
    if not allow(api_key):
        return JSONResponse({"detail":"Rate limit"}, status_code=429)
    return await call_next(request)
c) Tighten CORS

python
Copy
Edit
allowlist = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
app.add_middleware(CORSMiddleware, allow_origins=allowlist, allow_credentials=True,
                   allow_methods=["POST","GET","OPTIONS"], allow_headers=["Authorization","Content-Type"])
d) Harden extraction

Wrap Gemini → JSON behind try/except; reject if not valid JSON object with expected fields.

Add strict_mode that refuses low confidence (<0.7) merges and stores those in needs_confirmation.

3) compile_reports_refactor (1).py
Issues

Good start on patterns, but confidence is read from fact not from each support.

Severity mapping lacks coverage for “Subcontracts.”

Returns strings; should return structured result for programmatic use.

Patch

python
Copy
Edit
SEVERITY_LEVELS["moderate"].append("Subcontracts")

def validate_facts(facts):
    warnings, inconsistencies = [], []
    element_classifications = defaultdict(set)

    for fact in facts:
        element = fact.get("element","").strip()
        classification = fact.get("classification","").strip().lower()
        element_classifications[element].add(classification)

        # Per-support confidence
        for sup in fact.get("regulatory_support", []):
            conf = float(sup.get("confidence", fact.get("confidence", 0.0)))
            if conf < CONFIDENCE_THRESHOLD:
                warnings.append({
                  "severity":"warning","element":element,"issue":"low_confidence",
                  "detail": f"{conf:.2f}", "section": fact.get("source",{}).get("section","")
                })
        # Citation pattern check...
4) procurement_integrator.py
Issues

Imports timedelta but not from datetime (runtime NameError).

Calls Gemini in endpoint path; no timeouts/backoff; parse via fragile fence‑strip.

Knowledge graph path hardcoded; needs config.

Missing auth on router; recommend Depends(require_api_key).

Patch

python
Copy
Edit
from datetime import datetime, timedelta   # (add timedelta)
from apps.orchestrator.security import require_api_key

router = APIRouter(prefix="/procure", tags=["procurement"], dependencies=[Depends(require_api_key)])

# In gemini_check_compliance:
response = model.generate_content(prompt)
text = (response.text or "").strip()
try:
    payload = json.loads(text)
except json.JSONDecodeError:
    # attempt fenced or lax parse once
    payload = json.loads(re.sub(r"^```json|```$", "", text, flags=re.M))
And move graph path to env: KNOWLEDGE_GRAPH_PATH.

5) Reporting engine main.py
Issues

Imports seaborn (not strictly needed) and sets matplotlib style globally.

BigQuery/Storage clients created at import time; better lazy‑init.

No retries around BQ queries or GCS uploads.

Secrets fetched per request but not cached.

PDF gen OK, but saves temp files in /tmp only; fine, just ensure cleanup on failure.

Fixes

Remove seaborn import; use plain matplotlib.

Wrap BQ and Storage with retry/backoff; move client init into functions with caching (functools.lru_cache).

Ensure every external call is timed/logged.

6) DFARS templates / cover page / FY report
Issues

“Truncated for brevity”: convert templates into complete, versioned markdown in templates/render/md/….

FY assembler uses placeholders for costs/FY—add hooks to read from KB facts with proper keys; fail closed if data missing.

Fix

Introduce models.KBFact and adapters to compute FY aggregates from facts (even if initial is mocked, the seam is ready).

Runbook: how the pieces connect (end‑to‑end)
Discover EoC facts (RFP)

bash
Copy
Edit
python -m services.rfp_eoc_discovery.discovery --limit 200 > var/logs/discovery.log
# Outputs: var/outputs/RFP_Discovery_Report_<ts>.md
#          var/outputs/RFP_KB_Facts_<ts>.json
Validate facts (regex/quotes/confidence/consistency)

bash
Copy
Edit
python - <<'PY'
import json, sys
from services.rfp_eoc_discovery.validate import Item
from compile_reports_refactor import validate_facts

kb = json.load(open("var/outputs/RFP_KB_Facts_<ts>.json"))
warnings, inconsistencies = validate_facts(kb)
print(json.dumps({"warnings":warnings,"inconsistencies":inconsistencies}, indent=2))
PY
Assemble DFARS artifacts

bash
Copy
Edit
python templates/render/md/dfars_checklist_assembler.py \
  --in var/outputs/RFP_KB_Facts_<ts>.json --out var/outputs/DFARS_Checklist.md \
  --program "ACME SatCom" --contract "CPFF"

python templates/render/md/dfars_cover_page_assembler.py \
  --out var/outputs/DFARS_Cover_Page.md --program "ACME SatCom"
Annual FY report

bash
Copy
Edit
python templates/render/md/annual_fiscal_year_report_assembler.py \
  --in var/outputs/RFP_KB_Facts_<ts>.json --out var/outputs/Annual_FY_Report.md \
  --level "Resource" --program "ACME SatCom"
Orchestrator API online

bash
Copy
Edit
uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port 8000
# POST /orchestrate (stateful BOE), /validate-boe (compliance), /session/* (state)
Reporting engine

bash
Copy
Edit
uvicorn apps.reporting.main:app --host 0.0.0.0 --port 8080
# POST /reports/generate  (compliance_audit → PDF/Excel/JSON to GCS)
Unit tests + CI checks
Install test deps

toml
Copy
Edit
# pyproject.toml (snippets)
[project.optional-dependencies]
dev = ["pytest","pytest-asyncio","pytest-cov","httpx","ruff","mypy","types-requests","bandit","tenacity","pydantic-settings","freezegun","respx"]
Tests to add (examples)

Validation gates (quotes/regex/conf)

python
Copy
Edit
# tests/unit/test_validate.py
from services.rfp_eoc_discovery.validate import quote_ok, citation_ok
def test_quote_ok(): assert quote_ok("a " * 25); assert not quote_ok("a " * 26)
def test_citation_ok():
    assert citation_ok("Travel","DFARS","231.205-46")
    assert not citation_ok("Travel","FAR","31.201-2")
Cross‑reg consistency

python
Copy
Edit
# tests/unit/test_compile_reports_refactor.py
from compile_reports_refactor import validate_facts
def test_inconsistent_flags():
    facts=[{"element":"Travel","classification":"direct","regulatory_support":[],"source":{"section":"X"}},
           {"element":"Travel","classification":"indirect","regulatory_support":[],"source":{"section":"Y"}}]
    w,i=validate_facts(facts)
    assert any("Inconsistent classifications" in x for x in i)
Default‑deny auth

python
Copy
Edit
# tests/integration/test_auth.py
from fastapi.testclient import TestClient
from apps.orchestrator.main import app
def test_auth_required(monkeypatch):
    client = TestClient(app)
    r=client.post("/orchestrate", json={"user_message":"hi","session_id":"s"})
    assert r.status_code in (401,503)
Rate limiter

python
Copy
Edit
# tests/integration/test_rate_limit.py
def test_rate_limit(monkeypatch):
    # mock allow() to return False
    ...
    assert r.status_code==429
Orchestration extraction robustness

Use respx to stub Gemini endpoint and return malformed JSON → ensure HTTP 500 with clear error.

Valid JSON → state updated; confidence computed; missing fields surfaced.

Reporting engine

Patch BigQuery client to return small DF; ensure PDF/JSON build; assert files uploaded are mocked and URL returned.

Static analysis & security

ruff (lint/format), mypy (strict), bandit -r proposalos -ll (security).

pytest --cov=proposalos --cov-fail-under=80

GitHub Actions

yaml
Copy
Edit
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy proposalos
      - run: bandit -r proposalos -ll
      - run: pytest -q --cov=proposalos --cov-report=xml
What you’ll get after this pass
Cleaner module boundaries (LLM calls, validation, I/O are separable and testable).

Safer defaults (default‑deny auth, rate limiting, bounded egress).

Deterministic outputs you can ship to analysts (and defend in an audit).

CI that fails loudly on security/typing/coverage regressions.

If you want, I can turn this into a PR with the new folders and stubs wired up, or tailor the validators to your exact KB fact shape.
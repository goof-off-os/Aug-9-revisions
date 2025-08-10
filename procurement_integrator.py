"""
procurement_integrator.py
=========================
ProposalOS Procurement Integration Module
-----------------------------------------
This module adds procurement features to ProposalOS, including:
- RFP scraping from SAM.gov API.
- Subcontractor/vendor compliance validation (e.g., SAM exclusions, CMMC/NIST).
- Bill of Materials (BOM) generation for Direct Materials.
- Supply chain security checks (e.g., DFARS 252.204-7012, ITAR/EAR).
- Data rights/SNLR flagging.

Integrates with:
- Gemini for compliance checks (via gemini_integration_final.py).
- Knowledge graph for regulatory queries (via knowledge_graph_builder.py).
- Orchestrator for API endpoints (FastAPI-based).

Usage:
- Import into orchestrator_production.py for API exposure.
- Standalone functions for pipeline use (e.g., in compile_reports_refactor.py).

Dependencies:
- httpx (for API calls)
- google-generativeai (for Gemini)
- networkx (for graph queries)
- python-dotenv
- fastapi (if using endpoints)

Environment Vars (in LLM_MODEL_G.env or .env):
- SAM_API_KEY: SAM.gov API key
- GEMINI_API_KEY: Already loaded from LLM_MODEL_G.env

Compliance Notes:
- Aligns with FAR 15.404-3 (subcontract pricing), DFARS 252.244-7001 (purchasing system), NIST 800-171 (cybersecurity).
- Uses Hierarchy of Truth: Federal > RFP > Company > User.
"""

import os
import json
import logging
import httpx
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import networkx as nx  # For graph queries
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import google.generativeai as genai

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv("LLM_MODEL_G.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SAM_API_KEY = os.getenv("SAM_API_KEY")
if not SAM_API_KEY:
    logger.warning("SAM_API_KEY not set; RFP scraping will fail.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY required for compliance checks.")

genai.configure(api_key=GEMINI_API_KEY)

# FastAPI router for endpoints (import into orchestrator_production.py)
router = APIRouter(prefix="/procure", tags=["procurement"])

# Pydantic models for requests/responses
class ScrapeRFPRequest(BaseModel):
    keywords: str = "CPFF SatCom"
    limit: int = 10
    posted_from: str = (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")
    posted_to: str = datetime.now().strftime("%m/%d/%Y")

class SubcontractValidateRequest(BaseModel):
    vendor_name: str
    quote: float
    cmmc_certified: bool = False
    contract_type: str = "CPFF"

class BOMGenerateRequest(BaseModel):
    items: List[Dict[str, Any]]  # e.g., [{"item": "Component A", "quantity": 100, "unit_cost": 500}]
    estimated_budget: float
    contract_type: str = "CPFF"

class SecurityCheckRequest(BaseModel):
    vendor_name: str
    items: List[str]  # e.g., ["Software Module", "Hardware Component"]

# Dependency: Load knowledge graph (assume from knowledge_graph_builder.py)
def load_knowledge_graph(graph_path: str = "graph_outputs/knowledge_graph.graphml") -> nx.DiGraph:
    if not Path(graph_path).exists():
        raise ValueError(f"Knowledge graph not found at {graph_path}")
    return nx.read_graphml(graph_path)

# Helper: Gemini compliance call (adapted from gemini_integration_final.py)
async def gemini_check_compliance(data: Dict) -> Dict:
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = f"""
    Analyze for DoD procurement compliance:
    Data: {json.dumps(data, indent=2)}
    Check:
    1. FAR 15.403-4 (TINA) - $2M threshold
    2. DFARS 252.204-7012 - CUI protection
    3. CAS 401 - Cost consistency
    4. ITAR/EAR for export controls
    Return JSON: {{ "compliant": bool, "issues": list, "recommendations": list }}
    """
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text.strip().strip("```json").strip("```"))
    except Exception as e:
        logger.error(f"Gemini parse error: {e}")
        return {"compliant": False, "issues": [str(e)], "recommendations": []}

# Feature 1: RFP Scraping from SAM.gov
@router.post("/rfp_scrape")
async def scrape_rfps(request: ScrapeRFPRequest):
    url = "https://api.sam.gov/opportunities/v2/search"
    params = {
        "limit": request.limit,
        "api_key": SAM_API_KEY,
        "postedFrom": request.posted_from,
        "postedTo": request.posted_to,
        "title": request.keywords,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            logger.error(f"SAM.gov error: {response.text}")
            raise HTTPException(status_code=502, detail="SAM.gov API error")
        data = response.json().get("opportunitiesData", [])
        rfps = []
        for opp in data:
            rfp = {
                "id": opp["noticeId"],
                "title": opp["title"],
                "solicitation": opp["solicitationNumber"],
                "agency": opp["department"],
                "description": opp["description"],
            }
            # Extract procurement EoCs (e.g., Subcontracts)
            compliance = await gemini_check_compliance({"text": opp["description"]})
            rfp["compliance_issues"] = compliance["issues"]
            rfps.append(rfp)
        return {"rfps": rfps, "count": len(rfps)}

# Feature 2: Subcontractor Compliance Validation
@router.post("/subcontract_validate")
async def validate_subcontract(request: SubcontractValidateRequest):
    issues = []
    if request.quote > 2000000:
        issues.append("TINA compliance required (FAR 15.403-4)")
    if not request.cmmc_certified:
        issues.append("CMMC/NIST 800-171 required (DFARS 252.204-7012)")
    if request.contract_type == "CPFF":
        issues.append("Flowdown clauses per FAR 52.244-6")
    
    gemini_result = await gemini_check_compliance(request.dict())
    issues.extend(gemini_result["issues"])
    
    return {
        "vendor": request.vendor_name,
        "compliant": len(issues) == 0 and gemini_result["compliant"],
        "issues": issues,
        "recommendations": gemini_result["recommendations"]
    }

# Feature 3: BOM Generation
@router.post("/bom_generate")
async def generate_bom(request: BOMGenerateRequest):
    bom = []
    total = 0
    for item in request.items:
        unit_cost = item.get("unit_cost", 0)
        quantity = item.get("quantity", 0)
        extended = unit_cost * quantity
        total += extended
        compliance = await gemini_check_compliance({
            "item": item["item"],
            "cost": extended,
            "contract_type": request.contract_type
        })
        bom.append({
            "item": item["item"],
            "quantity": quantity,
            "unit_cost": unit_cost,
            "extended_cost": extended,
            "vendor": item.get("vendor", "Unknown"),
            "compliance_issues": compliance["issues"]
        })
    
    if total > request.estimated_budget:
        logger.warning(f"BOM exceeds budget: {total} > {request.estimated_budget}")
    
    return {"bom": bom, "total_cost": total, "within_budget": total <= request.estimated_budget}

# Feature 4: Supply Chain Security Check
@router.post("/security_check")
async def security_check(request: SecurityCheckRequest):
    graph = load_knowledge_graph()  # From knowledge_graph_builder.py
    issues = []
    
    # Query graph for DFARS/ITAR nodes
    try:
        dfars_nodes = [n for n, data in graph.nodes(data=True) if data.get("type") == "Regulation" and "DFARS" in data.get("system", "")]
        for node in dfars_nodes:
            if "252.204-7012" in graph.nodes[node]["label"]:
                issues.append("CUI protection required for vendor")
    except Exception as e:
        logger.error(f"Graph query error: {e}")
        issues.append("Graph query failed; manual DFARS check needed")
    
    gemini_result = await gemini_check_compliance({
        "vendor": request.vendor_name,
        "items": request.items,
        "contract_type": "CPFF"  # Default; make dynamic
    })
    issues.extend(gemini_result["issues"])
    
    return {"vendor": request.vendor_name, "items": request.items, "issues": issues, "compliant": len(issues) == 0}

# Standalone function: Integrate procurement facts into KB (call from compile_reports_refactor.py)
def add_procurement_to_kb(facts: List[Dict], procurement_data: Dict):
    # Example: Add vendor compliance as a fact
    new_fact = {
        "element": "Subcontracts",
        "classification": "direct",
        "rfp_relevance": f"Vendor {procurement_data['vendor_name']} compliance for {procurement_data['quote']}",
        "regulatory_support": [{"reg_title": "DFARS", "reg_section": "252.204-7012", "quote": "CUI protection required", "confidence": 0.95}],
        "notes": "Procurement integration"
    }
    facts.append(new_fact)
    return facts

if __name__ == "__main__":
    # For standalone testing
    import uvicorn
    app = FastAPI()
    app.include_router(router)
    uvicorn.run(app, host="0.0.0.0", port=8001)
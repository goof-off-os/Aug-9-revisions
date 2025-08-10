"""
ProposalOS Orchestrator - Procurement & KB Enhanced Edition
============================================================
Production orchestrator with procurement integration and knowledge graph connectivity

Version: 4.0.0
Features:
- Procurement validation (SAM.gov, DFARS compliance)
- Knowledge graph integration for regulatory citations
- Multi-turn NLI with conversation history
- Generational BOE refinement
- Circuit breakers for resilience
"""

import os
import json
import httpx
import redis
import hashlib
import hmac
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Set, Deque
from datetime import datetime, timedelta
from collections import deque
from functools import wraps
import secrets
from pathlib import Path
from enum import Enum
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential
import logging.handlers

from fastapi import FastAPI, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator, ValidationError
import google.generativeai as genai
from google.auth import default
from google.auth.transport.requests import Request as GoogleRequest
from google.cloud import firestore, logging as cloud_logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import io
import csv
from contextlib import asynccontextmanager
from circuit_breaker import CircuitBreaker

# --- Enhanced Logging with Rotation and GCP ---
class SanitizingFormatter(logging.Formatter):
    """Formatter that removes PII from logs"""
    PII_FIELDS = {'traveler_name', 'employee_id', 'contract_number', 'email', 'vendor_ein', 'cage_code'}
    
    def format(self, record):
        msg = super().format(record)
        for field in self.PII_FIELDS:
            if field in msg:
                msg = msg.replace(field, f"{field[:3]}***")
        return msg

# Configure logging with rotation
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    log_dir / "orchestrator.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(SanitizingFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

# GCP Cloud Logging if available
try:
    cloud_client = cloud_logging.Client()
    cloud_handler = cloud_client.get_default_handler()
    logger.addHandler(cloud_handler)
    logger.info("GCP Cloud Logging enabled")
except:
    logger.info("GCP Cloud Logging not available")

# --- Enhanced Metrics ---
request_counter = Counter('proposalOS_requests_total', 'Total requests', 
                          ['method', 'endpoint', 'status', 'user_id', 'session_type'])
request_duration = Histogram('proposalOS_request_duration_seconds', 'Request duration', 
                            ['method', 'endpoint'])
active_sessions = Gauge('proposalOS_active_sessions', 'Active sessions', ['type'])
model_call_duration = Histogram('proposalOS_model_call_duration_seconds', 'Model call duration', ['purpose'])
cache_hits = Counter('proposalOS_cache_hits_total', 'Cache hits', ['cache_type'])
error_counter = Counter('proposalOS_errors_total', 'Total errors', ['error_type', 'service'])
procurement_validations = Counter('proposalOS_procurement_validations', 'Procurement validations', ['vendor_type', 'result'])
kb_queries = Counter('proposalOS_kb_queries', 'Knowledge base queries', ['query_type'])

# --- Application Start Time ---
APP_START_TIME = time.monotonic()

# --- Load Gemini API Key ---
def load_gemini_api_key():
    """Load ONLY Gemini API key from LLM_MODEL_G.env file"""
    env_file = Path(__file__).parent / 'LLM_MODEL_G.env'
    if not env_file.exists():
        env_file = Path(__file__).parent.parent / 'LLM_MODEL_G.env'
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if 'GEMINI_API_KEY' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ['GEMINI_API_KEY'] = value.strip('"').strip("'")
                        logger.info("Loaded GEMINI_API_KEY from LLM_MODEL_G.env")
                        return
    else:
        logger.warning("LLM_MODEL_G.env not found, expecting GEMINI_API_KEY in environment")

load_gemini_api_key()

# --- Configuration ---
class Config:
    """Enhanced configuration with procurement settings"""
    
    REQUIRED_MODEL_VERSION = 'gemini-2.5-pro'
    
    def __init__(self):
        # Security
        self.API_KEY_HASH = os.environ.get('API_KEY_HASH')
        self.ALLOW_INSECURE = os.environ.get('ALLOW_INSECURE', 'false').lower() == 'true'
        if not self.API_KEY_HASH and not self.ALLOW_INSECURE:
            raise ValueError("API_KEY_HASH must be set or ALLOW_INSECURE=true for development")
        
        # CORS
        self.ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
        
        # Model
        self.GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
        self.MODEL_VERSION = os.environ.get('MODEL_VERSION', self.REQUIRED_MODEL_VERSION)
        if self.MODEL_VERSION != self.REQUIRED_MODEL_VERSION:
            logger.warning(f"Model version override: {self.MODEL_VERSION}")
        
        self.PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'proposalos-concept')
        
        # Services
        self.COMPLIANCE_SERVICE_URL = os.environ.get('COMPLIANCE_SERVICE_URL', 
            'https://compliance-validator-service-53179349611.us-central1.run.app')
        
        # Procurement Services
        self.SAM_GOV_API_KEY = os.environ.get('SAM_GOV_API_KEY')
        self.SAM_GOV_API_URL = os.environ.get('SAM_GOV_API_URL', 'https://api.sam.gov/entity-information/v3')
        self.FPDS_API_URL = os.environ.get('FPDS_API_URL', 'https://api.usa.gov/fpds')
        
        # Knowledge Base
        self.KB_FIRESTORE_COLLECTION = os.environ.get('KB_COLLECTION', 'knowledge_base_facts')
        self.GRAPH_SERVICE_URL = os.environ.get('GRAPH_SERVICE_URL', 'http://localhost:8001')
        
        # State management
        self.USE_REDIS = os.environ.get('USE_REDIS', 'false').lower() == 'true'
        self.USE_FIRESTORE = os.environ.get('USE_FIRESTORE', 'false').lower() == 'true'
        self.REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        
        # Rate limiting
        self.RATE_LIMIT = int(os.environ.get('RATE_LIMIT', '100'))
        self.RATE_LIMIT_WINDOW = 60
        
        # Session management
        self.SESSION_TTL = int(os.environ.get('SESSION_TTL', '3600'))
        self.MAX_SESSIONS_PER_USER = int(os.environ.get('MAX_SESSIONS_PER_USER', '5'))
        self.MAX_CONVERSATION_HISTORY = int(os.environ.get('MAX_CONVERSATION_HISTORY', '100'))
        
        # Generational settings
        self.MAX_GENERATIONS = int(os.environ.get('MAX_GENERATIONS', '3'))
        self.GENERATION_CONFIDENCE_THRESHOLD = float(os.environ.get('GENERATION_CONFIDENCE_THRESHOLD', '0.85'))
        
        # Circuit breaker settings
        self.CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.environ.get('CB_FAILURE_THRESHOLD', '5'))
        self.CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.environ.get('CB_RECOVERY_TIMEOUT', '60'))

config = Config()

# --- Circuit Breakers ---
gemini_breaker = CircuitBreaker(
    failure_threshold=config.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    expected_exception=Exception
)

compliance_breaker = CircuitBreaker(
    failure_threshold=config.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    expected_exception=httpx.RequestError
)

sam_gov_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=120,
    expected_exception=httpx.RequestError
)

# --- Data Models ---
class DataState(str, Enum):
    INCOMPLETE = "incomplete"
    PARTIAL = "partial"
    COMPLETE = "complete"
    VALIDATED = "validated"
    REFINED = "refined"  # After generational refinement

class ProcurementType(str, Enum):
    MATERIALS = "materials"
    SUBCONTRACT = "subcontract"
    COTS = "cots"
    ODC = "odc"
    SERVICES = "services"

class VendorData(BaseModel):
    """Vendor information for procurement validation"""
    cage_code: Optional[str] = Field(None, regex=r'^[A-Z0-9]{5}$')
    duns_number: Optional[str] = Field(None, regex=r'^\d{9}$')
    ein: Optional[str] = Field(None, regex=r'^\d{2}-\d{7}$')
    name: str
    address: Optional[str] = None
    sam_registered: Optional[bool] = None
    small_business: Optional[bool] = None
    
class SubcontractRequest(BaseModel):
    """Subcontract procurement request"""
    vendor_data: VendorData
    procurement_type: ProcurementType
    estimated_value: float = Field(gt=0)
    contract_type: str = Field(..., regex=r'^(FFP|CPFF|CPIF|T&M|IDIQ)$')
    flowdown_clauses: List[str] = []  # DFARS clauses to flow down
    itar_controlled: bool = False
    competition_type: str = Field(default="full", regex=r'^(full|limited|sole_source)$')
    justification: Optional[str] = None
    
class ProcurementValidationResponse(BaseModel):
    """Procurement validation results"""
    is_valid: bool
    vendor_status: Dict[str, Any]
    compliance_issues: List[Dict[str, str]]
    required_flowdowns: List[str]
    risk_score: float = Field(ge=0, le=100)
    recommendations: List[str]
    sam_exclusions: List[Dict[str, Any]] = []

class BOEData(BaseModel):
    """Enhanced BOE data with procurement elements"""
    element: str  # Direct Labor, Materials, Subcontracts, etc.
    classification: str  # direct, indirect, fee
    value: Optional[float] = None
    basis: Optional[str] = None
    regulatory_citations: List[str] = []
    confidence: float = Field(ge=0, le=1)
    generation: int = 1  # Which generation of refinement

class CostVolumeRequest(BaseModel):
    """Full cost volume generation request"""
    boe_elements: List[BOEData]
    procurement_items: List[SubcontractRequest] = []
    program_name: str
    contract_number: Optional[str] = None
    period_of_performance: str
    
# --- Knowledge Base Integration ---
class KnowledgeBaseService:
    """Service for querying knowledge base and graph"""
    
    def __init__(self, firestore_client, graph_url: str):
        self.firestore = firestore_client
        self.graph_url = graph_url
        self.cache = {}  # Simple in-memory cache
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def query_regulations(self, element: str, context: str) -> List[Dict[str, Any]]:
        """Query KB for regulatory citations"""
        kb_queries.labels(query_type='regulations').inc()
        
        cache_key = f"{element}:{context}"
        if cache_key in self.cache:
            cache_hits.labels(cache_type='kb').inc()
            return self.cache[cache_key]
        
        try:
            # Query Firestore KB
            if self.firestore:
                query = self.firestore.collection(config.KB_FIRESTORE_COLLECTION)\
                    .where('element', '==', element)\
                    .limit(10)
                
                docs = query.stream()
                results = []
                for doc in docs:
                    fact = doc.to_dict()
                    results.append({
                        'regulation': fact.get('regulatory_support', [{}])[0].get('reg_section', ''),
                        'quote': fact.get('regulatory_support', [{}])[0].get('quote', ''),
                        'confidence': fact.get('confidence', 0.5),
                        'url': fact.get('regulatory_support', [{}])[0].get('url', '')
                    })
                
                self.cache[cache_key] = results
                return results
                
        except Exception as e:
            logger.error(f"KB query error: {e}")
            error_counter.labels(error_type='kb_query', service='firestore').inc()
            
        return []
    
    async def query_graph(self, query: str) -> Dict[str, Any]:
        """Query knowledge graph for relationships"""
        kb_queries.labels(query_type='graph').inc()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.graph_url}/query",
                    json={"query": query},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Graph query error: {e}")
            error_counter.labels(error_type='graph_query', service='graph').inc()
            
        return {}

# --- Procurement Validation Service ---
class ProcurementService:
    """Service for procurement validation and compliance"""
    
    def __init__(self):
        self.sam_cache = {}
        self.dfars_flowdowns = {
            'DFARS 252.204-7012': 'Safeguarding Covered Defense Information',
            'DFARS 252.225-7001': 'Buy American',
            'DFARS 252.244-7000': 'Subcontracts for Commercial Items',
            'DFARS 252.223-7008': 'Prohibition of Hexavalent Chromium',
            'DFARS 252.246-7003': 'Notification of Potential Safety Issues'
        }
        
    @sam_gov_breaker
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def validate_vendor_sam(self, vendor: VendorData) -> Dict[str, Any]:
        """Validate vendor against SAM.gov"""
        procurement_validations.labels(vendor_type='sam', result='started').inc()
        
        # Check cache
        cache_key = vendor.cage_code or vendor.duns_number or vendor.ein
        if cache_key in self.sam_cache:
            cache_hits.labels(cache_type='sam').inc()
            return self.sam_cache[cache_key]
        
        try:
            headers = {
                'X-Api-Key': config.SAM_GOV_API_KEY,
                'Accept': 'application/json'
            }
            
            params = {}
            if vendor.cage_code:
                params['cageCode'] = vendor.cage_code
            elif vendor.duns_number:
                params['ueiDUNS'] = vendor.duns_number
                
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config.SAM_GOV_API_URL}/entities",
                    params=params,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = {
                        'registered': len(data.get('entityData', [])) > 0,
                        'active': data.get('entityData', [{}])[0].get('entityRegistration', {}).get('registrationStatus') == 'Active',
                        'exclusions': data.get('entityData', [{}])[0].get('exclusions', []),
                        'small_business': data.get('entityData', [{}])[0].get('assertions', {}).get('smallBusinessIndicator', False),
                        'cage_code': data.get('entityData', [{}])[0].get('cageCode'),
                        'expiration_date': data.get('entityData', [{}])[0].get('entityRegistration', {}).get('expirationDate')
                    }
                    
                    self.sam_cache[cache_key] = result
                    procurement_validations.labels(vendor_type='sam', result='success').inc()
                    return result
                else:
                    procurement_validations.labels(vendor_type='sam', result='not_found').inc()
                    return {'registered': False, 'exclusions': []}
                    
        except Exception as e:
            logger.error(f"SAM.gov validation error: {e}")
            error_counter.labels(error_type='sam_validation', service='sam_gov').inc()
            procurement_validations.labels(vendor_type='sam', result='error').inc()
            raise
    
    def get_required_flowdowns(self, request: SubcontractRequest) -> List[str]:
        """Determine required DFARS flowdown clauses"""
        required = ['DFARS 252.244-7000']  # Always required for subcontracts
        
        if request.estimated_value > 250000:
            required.append('DFARS 252.204-7012')  # Cybersecurity
            
        if request.itar_controlled:
            required.append('DFARS 252.225-7048')  # Export control
            
        if request.procurement_type == ProcurementType.MATERIALS:
            required.append('DFARS 252.225-7001')  # Buy American
            required.append('DFARS 252.223-7008')  # Hexavalent Chromium
            
        return required
    
    def calculate_risk_score(self, vendor_status: Dict, request: SubcontractRequest) -> float:
        """Calculate procurement risk score (0-100)"""
        score = 0.0
        
        # SAM registration (30 points)
        if not vendor_status.get('registered'):
            score += 30
        elif not vendor_status.get('active'):
            score += 15
            
        # Exclusions (40 points)
        if vendor_status.get('exclusions'):
            score += 40
            
        # Competition (15 points)
        if request.competition_type == 'sole_source':
            score += 15
        elif request.competition_type == 'limited':
            score += 7
            
        # Value threshold (15 points)
        if request.estimated_value > 1000000:
            score += 15
        elif request.estimated_value > 500000:
            score += 10
        elif request.estimated_value > 250000:
            score += 5
            
        return min(score, 100.0)

# --- Enhanced State Manager with Conversation History ---
class ConversationTurn(BaseModel):
    """Single conversation turn"""
    timestamp: datetime
    role: str  # user, assistant, system
    message: str
    extracted_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None

class EnhancedSessionState(BaseModel):
    """Enhanced session with full conversation history"""
    session_id: str
    user_id: str
    session_type: str  # boe, procurement, cost_volume
    created_at: datetime
    updated_at: datetime
    status: DataState
    
    # Conversation management
    conversation_history: Deque[ConversationTurn] = Field(default_factory=deque)
    current_generation: int = 1
    
    # BOE data
    boe_data: Optional[Dict[str, Any]] = None
    
    # Procurement data
    procurement_data: List[SubcontractRequest] = []
    vendor_validations: Dict[str, ProcurementValidationResponse] = {}
    
    # Cost volume data
    cost_volume: Optional[Dict[str, Any]] = None
    
    # Metadata
    completion_percentage: float = 0.0
    validation_results: List[Dict[str, Any]] = []
    kb_citations: List[Dict[str, Any]] = []
    
    class Config:
        arbitrary_types_allowed = True

# --- Enhanced Prompts ---
PROCUREMENT_NLI_PROMPT = """You are a procurement specialist assistant for government contracting.

Current context:
{context}

User query:
{query}

Parse the user's procurement request and extract:
1. Vendor information (name, CAGE code, DUNS if mentioned)
2. Procurement type (materials, subcontract, COTS, services)
3. Estimated value
4. Contract type (FFP, CPFF, T&M, etc.)
5. Any special requirements (ITAR, small business, etc.)

Also determine the user's intent:
- vendor_validation: Check vendor compliance
- flowdown_analysis: Determine required clauses
- risk_assessment: Evaluate procurement risk
- full_procurement: Complete procurement package

Return structured JSON:
{{
  "intent": "vendor_validation",
  "vendor_data": {{}},
  "procurement_details": {{}},
  "follow_up_questions": []
}}
"""

GENERATIONAL_REFINEMENT_PROMPT = """You are refining a BOE through iterative improvement.

Generation: {generation} of {max_generations}
Current BOE:
{current_boe}

Previous feedback:
{feedback}

Regulatory citations from KB:
{citations}

Refine the BOE to:
1. Improve regulatory compliance
2. Add missing citations
3. Clarify basis of estimate
4. Increase confidence score

Return the refined BOE with confidence score (0-1).
"""

# --- API Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced lifespan with service initialization"""
    logger.info("ProposalOS Orchestrator starting...")
    
    # Initialize Gemini
    genai.configure(api_key=config.GEMINI_API_KEY)
    app.state.model = genai.GenerativeModel(config.MODEL_VERSION)
    
    # Initialize Redis
    app.state.redis_client = None
    if config.USE_REDIS:
        try:
            app.state.redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
            app.state.redis_client.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
    
    # Initialize Firestore
    app.state.firestore_client = None
    if config.USE_FIRESTORE:
        try:
            app.state.firestore_client = firestore.Client(project=config.PROJECT_ID)
            logger.info("Firestore connected")
        except Exception as e:
            logger.error(f"Firestore connection failed: {e}")
    
    # Initialize services
    app.state.kb_service = KnowledgeBaseService(
        app.state.firestore_client,
        config.GRAPH_SERVICE_URL
    )
    app.state.procurement_service = ProcurementService()
    
    logger.info(f"ProposalOS Orchestrator ready (Model: {config.MODEL_VERSION})")
    
    yield
    
    logger.info("ProposalOS Orchestrator shutting down...")

app = FastAPI(
    title="ProposalOS Orchestrator - Procurement Enhanced",
    version="4.0.0",
    description="Production orchestrator with procurement and KB integration",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Security ---
security = HTTPBearer()

async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify API key with timing-safe comparison"""
    if config.ALLOW_INSECURE:
        return "dev_user"
    
    if not config.API_KEY_HASH:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    
    provided_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if not hmac.compare_digest(provided_hash, config.API_KEY_HASH):
        error_counter.labels(error_type='auth_failed', service='api').inc()
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return provided_hash[:8]

# --- Procurement Endpoints ---
@app.post("/procure/subcontract", response_model=ProcurementValidationResponse)
async def procure_subcontract(
    request: SubcontractRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_api_key)
):
    """Validate subcontract procurement against DFARS and SAM.gov"""
    start_time = time.time()
    
    try:
        # Validate vendor
        vendor_status = await app.state.procurement_service.validate_vendor_sam(request.vendor_data)
        
        # Get required flowdowns
        required_flowdowns = app.state.procurement_service.get_required_flowdowns(request)
        
        # Calculate risk
        risk_score = app.state.procurement_service.calculate_risk_score(vendor_status, request)
        
        # Check compliance
        compliance_issues = []
        
        if not vendor_status.get('registered'):
            compliance_issues.append({
                'severity': 'critical',
                'regulation': 'FAR 9.404',
                'issue': 'Vendor not registered in SAM.gov'
            })
            
        if vendor_status.get('exclusions'):
            compliance_issues.append({
                'severity': 'critical',
                'regulation': 'FAR 9.405',
                'issue': f"Vendor has {len(vendor_status['exclusions'])} active exclusions"
            })
            
        if request.competition_type == 'sole_source' and not request.justification:
            compliance_issues.append({
                'severity': 'high',
                'regulation': 'FAR 6.302',
                'issue': 'Sole source requires written justification'
            })
            
        # Missing flowdowns
        missing_flowdowns = set(required_flowdowns) - set(request.flowdown_clauses)
        if missing_flowdowns:
            compliance_issues.append({
                'severity': 'medium',
                'regulation': 'DFARS 252.244-7000',
                'issue': f"Missing required flowdown clauses: {', '.join(missing_flowdowns)}"
            })
        
        # Generate recommendations
        recommendations = []
        if risk_score > 70:
            recommendations.append("High risk procurement - consider additional oversight")
        if not vendor_status.get('small_business') and request.estimated_value < 250000:
            recommendations.append("Consider small business set-aside per FAR 19.502")
        if request.itar_controlled:
            recommendations.append("Ensure vendor has valid export license per ITAR 120.1")
            
        is_valid = len([i for i in compliance_issues if i['severity'] == 'critical']) == 0
        
        # Track metrics
        duration = time.time() - start_time
        request_duration.labels(method='POST', endpoint='/procure/subcontract').observe(duration)
        request_counter.labels(
            method='POST',
            endpoint='/procure/subcontract',
            status='200',
            user_id=user_id,
            session_type='procurement'
        ).inc()
        
        response = ProcurementValidationResponse(
            is_valid=is_valid,
            vendor_status=vendor_status,
            compliance_issues=compliance_issues,
            required_flowdowns=required_flowdowns,
            risk_score=risk_score,
            recommendations=recommendations,
            sam_exclusions=vendor_status.get('exclusions', [])
        )
        
        # Store in background
        if app.state.firestore_client:
            background_tasks.add_task(
                store_procurement_validation,
                request,
                response,
                user_id
            )
        
        return response
        
    except Exception as e:
        error_counter.labels(error_type='procurement_error', service='procurement').inc()
        logger.error(f"Procurement validation error: {e}")
        raise HTTPException(status_code=500, detail="Procurement validation failed")

@app.post("/procure/nli")
async def procurement_nli(
    query: str = Field(..., description="Natural language procurement query"),
    session_id: Optional[str] = None,
    user_id: str = Depends(verify_api_key)
):
    """Process natural language procurement requests"""
    try:
        # Get context from session if available
        context = {}
        if session_id:
            # Load session context
            pass
        
        prompt = PROCUREMENT_NLI_PROMPT.format(
            context=json.dumps(context),
            query=query
        )
        
        with model_call_duration.labels(purpose='procurement_nli').time():
            response = app.state.model.generate_content(prompt)
        
        parsed = json.loads(response.text)
        
        # Process based on intent
        if parsed['intent'] == 'vendor_validation':
            vendor_data = VendorData(**parsed['vendor_data'])
            vendor_status = await app.state.procurement_service.validate_vendor_sam(vendor_data)
            return {
                'intent': 'vendor_validation',
                'result': vendor_status,
                'follow_up': parsed.get('follow_up_questions', [])
            }
        
        return parsed
        
    except Exception as e:
        logger.error(f"Procurement NLI error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process procurement query")

# --- BOE Refinement with Generations ---
@app.post("/boe/refine")
async def refine_boe_generational(
    boe_data: BOEData,
    session_id: str,
    user_id: str = Depends(verify_api_key)
):
    """Refine BOE through generational improvement"""
    try:
        # Query KB for citations
        citations = await app.state.kb_service.query_regulations(
            boe_data.element,
            boe_data.basis or ""
        )
        kb_queries.labels(query_type='boe_refinement').inc()
        
        current_boe = boe_data.dict()
        feedback = ""
        
        for generation in range(1, config.MAX_GENERATIONS + 1):
            prompt = GENERATIONAL_REFINEMENT_PROMPT.format(
                generation=generation,
                max_generations=config.MAX_GENERATIONS,
                current_boe=json.dumps(current_boe),
                feedback=feedback,
                citations=json.dumps(citations)
            )
            
            with model_call_duration.labels(purpose='boe_refinement').time():
                response = app.state.model.generate_content(prompt)
            
            refined = json.loads(response.text)
            confidence = refined.get('confidence', 0.5)
            
            if confidence >= config.GENERATION_CONFIDENCE_THRESHOLD:
                # Sufficient confidence reached
                refined['generation'] = generation
                refined['regulatory_citations'] = [c['regulation'] for c in citations]
                
                active_sessions.labels(type='refined').inc()
                return refined
            
            # Prepare feedback for next generation
            feedback = f"Generation {generation} confidence: {confidence}. Need more specific regulatory basis."
            current_boe = refined
        
        # Max generations reached
        current_boe['generation'] = config.MAX_GENERATIONS
        current_boe['regulatory_citations'] = [c['regulation'] for c in citations]
        return current_boe
        
    except Exception as e:
        logger.error(f"BOE refinement error: {e}")
        error_counter.labels(error_type='refinement_error', service='boe').inc()
        raise HTTPException(status_code=500, detail="BOE refinement failed")

# --- Cost Volume Assembly ---
@app.post("/cost_volume/generate")
async def generate_cost_volume(
    request: CostVolumeRequest,
    user_id: str = Depends(verify_api_key)
):
    """Generate complete cost volume with BOEs and procurement"""
    try:
        cost_volume = {
            'program_name': request.program_name,
            'contract_number': request.contract_number,
            'period_of_performance': request.period_of_performance,
            'generated_at': datetime.now().isoformat(),
            'elements': []
        }
        
        # Process BOE elements
        for boe in request.boe_elements:
            # Get KB citations
            citations = await app.state.kb_service.query_regulations(
                boe.element,
                boe.basis or ""
            )
            
            element = {
                'element': boe.element,
                'classification': boe.classification,
                'value': boe.value,
                'basis': boe.basis,
                'citations': citations,
                'confidence': boe.confidence
            }
            cost_volume['elements'].append(element)
        
        # Process procurement items
        procurement_results = []
        for proc_request in request.procurement_items:
            result = await app.state.procurement_service.validate_vendor_sam(proc_request.vendor_data)
            flowdowns = app.state.procurement_service.get_required_flowdowns(proc_request)
            
            procurement_results.append({
                'vendor': proc_request.vendor_data.name,
                'type': proc_request.procurement_type,
                'value': proc_request.estimated_value,
                'validation': result,
                'required_flowdowns': flowdowns
            })
        
        cost_volume['procurement'] = procurement_results
        
        # Calculate totals
        direct_total = sum(e.value or 0 for e in request.boe_elements if e.classification == 'direct')
        indirect_total = sum(e.value or 0 for e in request.boe_elements if e.classification == 'indirect')
        procurement_total = sum(p.estimated_value for p in request.procurement_items)
        
        cost_volume['summary'] = {
            'direct_costs': direct_total,
            'indirect_costs': indirect_total,
            'procurement': procurement_total,
            'total': direct_total + indirect_total + procurement_total
        }
        
        return cost_volume
        
    except Exception as e:
        logger.error(f"Cost volume generation error: {e}")
        raise HTTPException(status_code=500, detail="Cost volume generation failed")

# --- Helper Functions ---
async def store_procurement_validation(request: SubcontractRequest, response: ProcurementValidationResponse, user_id: str):
    """Store procurement validation in Firestore"""
    try:
        doc = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'vendor_name': request.vendor_data.name,
            'procurement_type': request.procurement_type,
            'estimated_value': request.estimated_value,
            'risk_score': response.risk_score,
            'is_valid': response.is_valid,
            'compliance_issues': response.compliance_issues
        }
        
        app.state.firestore_client.collection('procurement_validations').add(doc)
        logger.info(f"Stored procurement validation for {request.vendor_data.name}")
        
    except Exception as e:
        logger.error(f"Failed to store procurement validation: {e}")

# --- Health and Metrics ---
@app.get("/health")
async def health_check():
    """Enhanced health check"""
    uptime = time.monotonic() - APP_START_TIME
    
    return {
        "status": "healthy",
        "service": "proposalOS-orchestrator-procurement",
        "version": "4.0.0",
        "uptime_seconds": round(uptime, 2),
        "model_version": config.MODEL_VERSION,
        "components": {
            "gemini": "connected" if hasattr(app.state, 'model') else "disconnected",
            "redis": "connected" if app.state.redis_client else "disabled",
            "firestore": "connected" if app.state.firestore_client else "disabled",
            "sam_gov": "configured" if config.SAM_GOV_API_KEY else "disabled",
            "kb_service": "ready" if hasattr(app.state, 'kb_service') else "disabled"
        },
        "circuit_breakers": {
            "gemini": gemini_breaker.state.name,
            "compliance": compliance_breaker.state.name,
            "sam_gov": sam_gov_breaker.state.name
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
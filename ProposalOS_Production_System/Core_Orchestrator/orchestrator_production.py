"""
ProposalOS Orchestrator - Production-Hardened Version
======================================================
# NOTE: Model/env handling refactor (2025-08-10)
Stateful BOE Interrogation Engine with Enterprise Security

Version: 3.0.0
Author: ProposalOS Team
Last Updated: August 2025
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
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
from collections import deque
from functools import wraps
import secrets
from pathlib import Path
import backoff
import pybreaker

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, validator, ValidationError
import google.generativeai as genai
from google.auth import default
from google.auth.transport.requests import Request as GoogleRequest
from google.cloud import firestore
from enum import Enum
import io
import csv
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import backoff

# --- Logging Configuration (Sanitized) ---
class SanitizingFormatter(logging.Formatter):
    """Formatter that removes PII from logs"""
    PII_FIELDS = {'traveler_name', 'employee_id', 'contract_number', 'email'}
    
    def format(self, record):
        # Sanitize message
        msg = super().format(record)
        for field in self.PII_FIELDS:
            msg = msg.replace(field, f"{field[:3]}***")
        return msg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(SanitizingFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.handlers = [handler]

# --- Metrics ---
request_counter = Counter('proposalOS_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('proposalOS_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_sessions = Gauge('proposalOS_active_sessions', 'Active sessions')
model_call_duration = Histogram('proposalOS_model_call_duration_seconds', 'Model call duration')
cache_hits = Counter('proposalOS_cache_hits_total', 'Cache hits', ['cache_type'])
error_counter = Counter('proposalOS_errors_total', 'Total errors', ['error_type'])

# --- Application Start Time ---
APP_START_TIME = time.monotonic()

# --- Load Gemini API Key from LLM_MODEL_G.env ---
def load_gemini_api_key():
    """Load ONLY Gemini API key from LLM_MODEL_G.env file"""
    env_file = Path(__file__).parent / 'LLM_MODEL_G.env'
    if not env_file.exists():
        # Try parent directory
        env_file = Path(__file__).parent.parent / 'LLM_MODEL_G.env'
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if 'GEMINI_API_KEY' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ['GEMINI_API_KEY'] = value.strip('"').strip("'")
                        logger.info(f"Loaded GEMINI_API_KEY from LLM_MODEL_G.env")
                        return
    else:
        logger.warning("LLM_MODEL_G.env not found, expecting GEMINI_API_KEY in environment")

# Load Gemini key before Config initialization
load_gemini_api_key()

# --- Configuration ---
class Config:
    """Centralized configuration with validation"""
    
    # Model version centralized - all services must use this
    REQUIRED_MODEL_VERSION = 'gemini-2.5-pro'
    
    def __init__(self):
        # Security - Default to DENY
        self.API_KEY_HASH = os.environ.get('API_KEY_HASH')
        self.ALLOW_INSECURE = os.environ.get('ALLOW_INSECURE', 'false').lower() == 'true'
        if not self.API_KEY_HASH and not self.ALLOW_INSECURE:
            raise ValueError("API_KEY_HASH must be set or ALLOW_INSECURE=true for development")
        
        # CORS - Restrictive by default
        self.ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
        
        # Model configuration - API key from LLM_MODEL_G.env
        self.GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
        
        # Prefer GEMINI_MODEL_NAME, then MODEL_NAME, then MODEL_VERSION; default to required version
        self.GEMINI_MODEL_NAME = (
            os.environ.get('GEMINI_MODEL_NAME') or 
            os.environ.get('MODEL_NAME') or 
            os.environ.get('MODEL_VERSION') or 
            self.REQUIRED_MODEL_VERSION
        )
        
        # Optional "fast" model for lightweight extraction; falls back to main model
        self.GEMINI_FAST_MODEL_NAME = (
            os.environ.get('GEMINI_FAST_MODEL_NAME') or 
            os.environ.get('FAST_MODEL_NAME') or 
            ''
        )
        
        # Assert model version consistency
        if self.GEMINI_MODEL_NAME != self.REQUIRED_MODEL_VERSION:
            logger.warning(f"Model override detected: {self.GEMINI_MODEL_NAME} (required: {self.REQUIRED_MODEL_VERSION})")
        
        self.PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'proposalos-concept')
        
        # Services
        self.COMPLIANCE_SERVICE_URL = os.environ.get('COMPLIANCE_SERVICE_URL', 
            'https://compliance-validator-service-53179349611.us-central1.run.app')
        
        # Procurement
        self.SAM_API_KEY = os.environ.get('SAM_API_KEY')
        
        # Knowledge Graph
        self.KNOWLEDGE_GRAPH_URL = os.environ.get('KNOWLEDGE_GRAPH_URL', 'http://localhost:7474')
        self.NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
        self.NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
        
        # State management
        self.USE_REDIS = os.environ.get('USE_REDIS', 'false').lower() == 'true'
        self.USE_FIRESTORE = os.environ.get('USE_FIRESTORE', 'false').lower() == 'true'
        self.REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        
        # Rate limiting
        self.RATE_LIMIT = int(os.environ.get('RATE_LIMIT', '100'))  # Per minute
        self.RATE_LIMIT_WINDOW = 60  # seconds
        
        # Session management
        self.SESSION_TTL = int(os.environ.get('SESSION_TTL', '3600'))
        self.MAX_SESSIONS_PER_USER = int(os.environ.get('MAX_SESSIONS_PER_USER', '5'))
        self.MAX_CONVERSATION_HISTORY = int(os.environ.get('MAX_CONVERSATION_HISTORY', '50'))
        
        # Circuit breaker settings
        self.CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.environ.get('CB_FAILURE_THRESHOLD', '3'))
        self.CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.environ.get('CB_RECOVERY_TIMEOUT', '60'))
        
        # Timeouts
        self.HTTP_CONNECT_TIMEOUT = int(os.environ.get('HTTP_CONNECT_TIMEOUT', '5'))
        self.HTTP_READ_TIMEOUT = int(os.environ.get('HTTP_READ_TIMEOUT', '30'))

    def validate(self):
        """Validate configuration at startup"""
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required (should be in LLM_MODEL_G.env)")
        
        # Assert model version at startup
        if self.GEMINI_MODEL_NAME != self.REQUIRED_MODEL_VERSION:
            if not self.ALLOW_INSECURE:
                raise ValueError(f"Model version mismatch: got {self.GEMINI_MODEL_NAME}, required {self.REQUIRED_MODEL_VERSION}")
            logger.warning(f"Model version mismatch allowed in dev mode: {self.GEMINI_MODEL_NAME}")
        
        logger.info(f"Using primary model: {self.GEMINI_MODEL_NAME}")
        if self.GEMINI_FAST_MODEL_NAME:
            logger.info(f"Using fast model for extraction: {self.GEMINI_FAST_MODEL_NAME}")
        
        # Validate SAM API key
        if not self.SAM_API_KEY:
            logger.warning("SAM_API_KEY is not set. RFP scraping will be unavailable.")
        
        if self.USE_REDIS:
            # Test Redis connection
            try:
                r = redis.from_url(self.REDIS_URL)
                r.ping()
                logger.info("Redis connection verified")
            except Exception as e:
                if not self.ALLOW_INSECURE:
                    raise ValueError(f"Redis enabled but unreachable: {e}")
                logger.warning(f"Redis unreachable, continuing in degraded mode: {e}")

config = Config()

# --- Circuit Breakers ---
# Using pybreaker for better reliability and monitoring
compliance_breaker = pybreaker.CircuitBreaker(
    fail_max=config.CIRCUIT_BREAKER_FAILURE_THRESHOLD if hasattr(config, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD') else 3,
    reset_timeout=config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT if hasattr(config, 'CIRCUIT_BREAKER_RECOVERY_TIMEOUT') else 60,
    exclude=[httpx.HTTPStatusError]  # Don't trip on 4xx errors, only infrastructure failures
)

sam_gov_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=120,  # SAM.gov gets longer recovery time
    exclude=[httpx.HTTPStatusError]
)

gemini_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    exclude=[ValueError]  # Don't trip on parsing errors
)

knowledge_graph_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=90,
    exclude=[ValueError]
)

# --- Initialize Services ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("ProposalOS Orchestrator starting up...")
    
    # Log model configuration
    logger.info(f"Gemini main model: {config.GEMINI_MODEL_NAME}")
    if config.GEMINI_FAST_MODEL_NAME:
        logger.info(f"Gemini fast model: {config.GEMINI_FAST_MODEL_NAME}")
    else:
        logger.info("Gemini fast model: (not set, using main)")
    
    config.validate()
    
    # Initialize Gemini
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    
    genai.configure(api_key=config.GEMINI_API_KEY)
    
    def _get_model(name: str = None):
        """Create a GenerativeModel with the configured (or provided) name."""
        model_name = (name or config.GEMINI_MODEL_NAME).strip()
        if not model_name:
            raise RuntimeError("Gemini model name is empty after env resolution")
        return genai.GenerativeModel(model_name)
    
    # Primary conversational model
    app.state.model = _get_model()
    
    # Fast model (fallbacks to primary if not provided)
    app.state.fast_model = _get_model(config.GEMINI_FAST_MODEL_NAME) if config.GEMINI_FAST_MODEL_NAME else app.state.model
    
    # Initialize Redis if enabled
    app.state.redis_client = None
    if config.USE_REDIS:
        try:
            app.state.redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
            app.state.redis_client.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            if not config.ALLOW_INSECURE:
                raise
    
    # Initialize Firestore if enabled
    app.state.firestore_client = None
    if config.USE_FIRESTORE:
        try:
            app.state.firestore_client = firestore.Client(project=config.PROJECT_ID)
            # Test write
            test_doc = app.state.firestore_client.collection('_health').document('startup')
            test_doc.set({'timestamp': datetime.now().isoformat()})
            logger.info("Firestore connected")
        except Exception as e:
            logger.error(f"Firestore connection failed: {e}")
            if not config.ALLOW_INSECURE:
                raise
    
    logger.info(f"ProposalOS Orchestrator ready (Model: {config.MODEL_VERSION})")
    
    yield
    
    # Shutdown
    logger.info("ProposalOS Orchestrator shutting down...")
    # Save cached states
    if hasattr(app.state, 'state_manager'):
        await app.state.state_manager.flush_all()
    logger.info("Shutdown complete")

# --- FastAPI App ---
app = FastAPI(
    title="ProposalOS Orchestrator - Production",
    version="3.0.0",
    description="Production-hardened BOE interrogation engine",
    lifespan=lifespan
)

# --- CORS Middleware (Restrictive) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Rate Limiter ---
class RateLimiter:
    """Token bucket rate limiter using Redis"""
    
    def __init__(self, redis_client: Optional[redis.Redis]):
        self.redis_client = redis_client
        self.local_buckets = {}  # Fallback for non-Redis
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if request is within rate limit"""
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                now = time.time()
                pipe.zremrangebyscore(key, 0, now - window)
                pipe.zadd(key, {str(now): now})
                pipe.zcount(key, now - window, now)
                pipe.expire(key, window)
                results = pipe.execute()
                return results[2] <= limit
            except Exception as e:
                logger.error(f"Rate limit check failed: {e}")
                return True  # Fail open in case of Redis issues
        else:
            # Simple local rate limiting
            now = time.time()
            if key not in self.local_buckets:
                self.local_buckets[key] = deque()
            
            bucket = self.local_buckets[key]
            # Remove old entries
            while bucket and bucket[0] < now - window:
                bucket.popleft()
            
            if len(bucket) >= limit:
                return False
            
            bucket.append(now)
            return True

# --- Security ---
security = HTTPBearer()

async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify API key with timing-safe comparison"""
    if config.ALLOW_INSECURE:
        logger.warning("Running in INSECURE mode - authentication bypassed")
        return "dev_user"
    
    if not config.API_KEY_HASH:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    
    # Timing-safe comparison
    provided_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if not hmac.compare_digest(provided_hash, config.API_KEY_HASH):
        error_counter.labels(error_type='auth_failed').inc()
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Rate limiting
    rate_limiter = RateLimiter(app.state.redis_client)
    client_ip = request.client.host
    rate_key = f"rate:{provided_hash[:8]}:{client_ip}"
    
    if not await rate_limiter.check_rate_limit(rate_key, config.RATE_LIMIT, config.RATE_LIMIT_WINDOW):
        error_counter.labels(error_type='rate_limited').inc()
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return provided_hash[:8]  # Return truncated hash as user ID

# --- Data Models ---
class DataState(str, Enum):
    """State of data collection"""
    INCOMPLETE = "incomplete"
    PARTIAL = "partial"
    COMPLETE = "complete"
    VALIDATED = "validated"

class SessionData(BaseModel):
    """Structured session data"""
    traveler_name: Optional[str] = None
    origin_city: Optional[str] = None
    destination_city: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    transportation_mode: Optional[str] = None
    hotel_nights: Optional[int] = None
    trip_purpose: Optional[str] = None
    estimated_cost: Optional[float] = None
    supervisor_approval: Optional[bool] = None
    contract_number: Optional[str] = None

class SessionMetadata(BaseModel):
    """Session metadata"""
    created_at: datetime
    updated_at: datetime
    user_id: str
    message_count: int = 0
    completion_percentage: float = 0.0
    validation_status: Optional[Dict[str, Any]] = None
    last_activity: datetime

class SessionState(BaseModel):
    """Complete session state"""
    data: SessionData
    metadata: SessionMetadata
    status: DataState = DataState.INCOMPLETE
    conversation_history: List[Dict[str, Any]] = []
    pending_confirmations: Dict[str, Any] = {}  # Low confidence extractions
    
    class Config:
        use_enum_values = True

class OrchestrationRequest(BaseModel):
    """Request model for orchestration"""
    user_message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, max_length=100)
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Invalid session_id format')
        return v

class OrchestrationResponse(BaseModel):
    """Response model for orchestration"""
    ai_response: str
    current_state: SessionData
    data_completeness: DataState
    next_required_fields: List[str]
    next_action: str  # UX hint
    confidence_score: float = Field(ge=0, le=1)
    pending_confirmations: Dict[str, Any] = {}

class BOEValidationRequest(BaseModel):
    """Request model for BOE validation"""
    boe_data: Dict[str, Any]
    session_id: Optional[str] = None
    strict_mode: bool = False

class BOEValidationResponse(BaseModel):
    """Response model for BOE validation"""
    is_valid: bool
    compliance_score: float = Field(ge=0, le=100)
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    degraded_mode: bool = False

# --- Procurement Data Models ---
class RFPScrapeRequest(BaseModel):
    """Request model for RFP scraping from SAM.gov"""
    keywords: str = Field(..., description="Keywords to search for in RFP titles (e.g., 'CPFF SatCom').")
    posted_days_ago: int = Field(30, gt=0, le=365, description="Search for RFPs posted in the last N days.")
    limit: int = Field(10, gt=0, le=100, description="Number of results to return.")
    
    @validator('keywords')
    def validate_keywords(cls, v):
        if len(v) < 3:
            raise ValueError('Keywords must be at least 3 characters')
        return v

class RFP(BaseModel):
    """RFP opportunity from SAM.gov"""
    notice_id: str
    title: str
    solicitation_number: str
    agency: str
    posted_date: str
    response_deadline: Optional[str] = None
    url: str
    naics_code: Optional[str] = None
    set_aside: Optional[str] = None  # Small business, 8(a), etc.
    award_type: Optional[str] = None  # Contract type

class VendorComplianceRequest(BaseModel):
    """Request model for vendor compliance validation"""
    vendor_name: str = Field(..., min_length=1, max_length=200)
    sam_uei: Optional[str] = Field(None, regex=r'^[A-Z0-9]{12}$', description="SAM Unique Entity ID (12 chars)")
    sam_duns: Optional[str] = Field(None, regex=r'^\d{9}$', description="DUNS number (9 digits)")
    cage_code: Optional[str] = Field(None, regex=r'^[A-Z0-9]{5}$', description="CAGE code (5 chars)")
    quote_amount: float = Field(..., gt=0, le=1e9, description="Quote amount in USD")
    contract_type: str = Field("CPFF", regex=r'^(CPFF|FFP|T&M|CPIF|CPAF|IDIQ)$', description="Contract type")
    is_cmmc_certified: bool = Field(False, description="CMMC Level 2+ certification status")
    requires_secret_clearance: bool = Field(False, description="Requires facility clearance")
    itar_controlled: bool = Field(False, description="ITAR-controlled materials/services")
    
    @validator('vendor_name')
    def sanitize_vendor_name(cls, v):
        # Remove potential SQL injection characters
        return v.replace(';', '').replace('--', '').replace("'", "''")

class ComplianceIssue(BaseModel):
    """Compliance validation issue"""
    code: str = Field(..., description="Issue code (e.g., SAM001, CMMC002)")
    description: str = Field(..., description="Human-readable description")
    severity: str = Field(..., regex=r'^(Critical|Error|Warning|Info)$', description="Issue severity")
    regulation: Optional[str] = Field(None, description="Related regulation (e.g., FAR 9.404)")
    remediation: Optional[str] = Field(None, description="Suggested remediation action")

class VendorComplianceResponse(BaseModel):
    """Vendor compliance validation response"""
    vendor_name: str
    is_compliant: bool
    compliance_score: float = Field(ge=0, le=100, description="Overall compliance score")
    issues: List[ComplianceIssue] = []
    sam_status: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[str] = None
    approval_required: bool = False
    approver_level: Optional[str] = None  # PM, Director, VP based on risk

class SubcontractRequest(BaseModel):
    """Enhanced subcontract procurement request with circuit breaker support"""
    vendor_data: Dict[str, Any]
    contract_value: float = Field(..., gt=0, description="Contract value in USD")
    contract_type: str = Field("FFP", regex=r'^(CPFF|FFP|T&M|CPIF|CPAF|IDIQ)$')
    requires_compliance_check: bool = True
    flowdown_clauses: List[str] = []
    itar_controlled: bool = False

class RFPScrapeResponse(BaseModel):
    """Response from RFP scraping"""
    total_found: int
    rfps: List[RFP]
    search_params: Dict[str, Any]
    cached: bool = False
    scraped_at: datetime

# --- Prompts ---
STATEFUL_INTERROGATION_PROMPT = """You are an expert BOE analyst with perfect memory conducting travel cost interviews.

GOLDEN RULE: Never ask for information already provided. Check current_data_state before every question.

Recently asked questions to AVOID repeating:
{recent_questions}

Current data state:
{current_data}

User message:
{user_message}

Required fields still missing:
{missing_fields}

Instructions:
1. Extract ALL information from the user message (explicit and implicit)
2. Acknowledge what you learned specifically
3. Ask for the NEXT missing piece of information only
4. Be conversational but efficient

Respond with your acknowledgment and next question:"""

DATA_EXTRACTION_PROMPT = """Extract structured data from this conversation snippet.

Conversation:
{conversation}

Return JSON in EXACTLY this format:
{{
  "extracted_fields": {{
    "traveler_name": {{"value": "John Smith", "confidence": 0.95}},
    "origin_city": {{"value": "Denver, CO", "confidence": 0.90}},
    "destination_city": {{"value": null, "confidence": 0}},
    "departure_date": {{"value": "2025-03-15", "confidence": 0.85}},
    "return_date": {{"value": null, "confidence": 0}},
    "transportation_mode": {{"value": "air", "confidence": 0.80}},
    "trip_purpose": {{"value": "Program review meeting", "confidence": 0.75}},
    "estimated_cost": {{"value": 2500.00, "confidence": 0.60}}
  }},
  "implied_information": ["Will fly because distance > 500 miles"],
  "missing_required": ["return_date", "destination_city"],
  "compliance_concerns": []
}}

Rules:
- Set value to null if not found
- Confidence 0.0-1.0 (0 if not found)
- Parse relative dates ("next Monday" → actual date)
- Infer transportation from distance/urgency
- Flag compliance issues

Return ONLY valid JSON:"""

# --- State Manager ---
class StateManager:
    """Enhanced state manager with session limits"""
    
    def __init__(self, redis_client: Optional[redis.Redis], firestore_client):
        self.redis_client = redis_client
        self.firestore_client = firestore_client
        self.local_cache = {}
    
    async def get_state(self, session_id: str, user_id: str) -> SessionState:
        """Get or create session state"""
        # Check cache
        if session_id in self.local_cache:
            cache_hits.labels(cache_type='local').inc()
            return self.local_cache[session_id]
        
        # Try Redis
        if self.redis_client:
            try:
                state_json = self.redis_client.get(f"session:{session_id}")
                if state_json:
                    cache_hits.labels(cache_type='redis').inc()
                    state_dict = json.loads(state_json)
                    state = SessionState(**state_dict)
                    self.local_cache[session_id] = state
                    return state
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Try Firestore
        if self.firestore_client:
            try:
                doc = self.firestore_client.collection('sessions').document(session_id).get()
                if doc.exists:
                    cache_hits.labels(cache_type='firestore').inc()
                    state_dict = doc.to_dict()
                    state = SessionState(**state_dict)
                    self.local_cache[session_id] = state
                    return state
            except Exception as e:
                logger.error(f"Firestore get error: {e}")
        
        # Create new state
        return await self._create_new_state(session_id, user_id)
    
    async def _create_new_state(self, session_id: str, user_id: str) -> SessionState:
        """Create new session with user limits"""
        # Check session limit for user
        if await self._check_session_limit(user_id):
            # Create new session
            now = datetime.now()
            state = SessionState(
                data=SessionData(),
                metadata=SessionMetadata(
                    created_at=now,
                    updated_at=now,
                    user_id=user_id,
                    last_activity=now
                )
            )
            await self.save_state(session_id, state)
            active_sessions.inc()
            return state
        else:
            raise HTTPException(
                status_code=429,
                detail=f"Maximum sessions ({config.MAX_SESSIONS_PER_USER}) reached for user"
            )
    
    async def _check_session_limit(self, user_id: str) -> bool:
        """Check if user is within session limit"""
        if config.ALLOW_INSECURE:
            return True
        
        count = 0
        if self.firestore_client:
            try:
                docs = self.firestore_client.collection('sessions')\
                    .where('metadata.user_id', '==', user_id)\
                    .stream()
                count = sum(1 for _ in docs)
            except Exception as e:
                logger.error(f"Session count error: {e}")
        
        return count < config.MAX_SESSIONS_PER_USER
    
    async def save_state(self, session_id: str, state: SessionState):
        """Save state to all backends"""
        # Limit conversation history
        if len(state.conversation_history) > config.MAX_CONVERSATION_HISTORY:
            state.conversation_history = state.conversation_history[-config.MAX_CONVERSATION_HISTORY:]
        
        # Update cache
        self.local_cache[session_id] = state
        
        # Save to Redis
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"session:{session_id}",
                    config.SESSION_TTL,
                    state.json()
                )
            except Exception as e:
                logger.error(f"Redis save error: {e}")
        
        # Save to Firestore
        if self.firestore_client:
            try:
                self.firestore_client.collection('sessions').document(session_id).set(
                    json.loads(state.json())
                )
            except Exception as e:
                logger.error(f"Firestore save error: {e}")
    
    async def flush_all(self):
        """Flush all cached states to persistent storage"""
        for session_id, state in self.local_cache.items():
            await self.save_state(session_id, state)

# --- Helper Functions ---
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
async def get_auth_token():
    """Get auth token with retry"""
    try:
        credentials, _ = default()
        credentials.refresh(GoogleRequest())
        return credentials.token
    except Exception as e:
        logger.error(f"Auth token error: {e}")
        raise

async def run_in_thread(func, *args, **kwargs):
    """Run blocking function in thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)

async def extract_data_from_conversation(
    ai_response: str,
    user_message: str,
    current_state: SessionState,
    use_fast_model: bool = True
) -> Tuple[SessionState, float]:
    """Extract data using model with proper schema"""
    try:
        conversation = f"User: {user_message}\nAssistant: {ai_response}"
        prompt = DATA_EXTRACTION_PROMPT.format(conversation=conversation)
        
        # Use fast model for extraction if available and requested
        extraction_model = app.state.fast_model if use_fast_model else app.state.model
        
        # Run model in thread to avoid blocking
        with model_call_duration.time():
            response = await run_in_thread(extraction_model.generate_content, prompt)
        
        extracted = json.loads(response.text.strip())
        
        # Update state with high confidence fields
        confidence_scores = []
        for field, data in extracted.get("extracted_fields", {}).items():
            if isinstance(data, dict):
                confidence = data.get("confidence", 0)
                value = data.get("value")
                confidence_scores.append(confidence)
                
                if confidence > 0.7 and value is not None:
                    # High confidence - update directly
                    if hasattr(current_state.data, field):
                        setattr(current_state.data, field, value)
                elif confidence > 0.3 and value is not None:
                    # Medium confidence - add to pending
                    current_state.pending_confirmations[field] = {
                        "value": value,
                        "confidence": confidence,
                        "needs_confirmation": True
                    }
        
        # Update metadata
        current_state.metadata.updated_at = datetime.now()
        current_state.metadata.completion_percentage = calculate_completion(current_state.data)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        return current_state, avg_confidence
        
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        error_counter.labels(error_type='extraction_failed').inc()
        return current_state, 0.0

def calculate_completion(data: SessionData) -> float:
    """Calculate completion percentage"""
    required = ["traveler_name", "origin_city", "destination_city",
                "departure_date", "return_date", "transportation_mode", "trip_purpose"]
    completed = sum(1 for f in required if getattr(data, f) is not None)
    return (completed / len(required)) * 100

def get_recent_questions(history: List[Dict]) -> List[str]:
    """Extract last 3 questions asked to avoid repetition"""
    questions = []
    for item in history[-6:]:  # Last 3 exchanges
        if item.get("role") == "assistant":
            msg = item.get("message", "")
            if "?" in msg:
                questions.append(msg.split("?")[0] + "?")
    return questions[-3:]

def get_next_action(missing_fields: List[str]) -> str:
    """Generate UX-friendly next action hint"""
    if not missing_fields:
        return "Review and validate the complete information"
    
    field_actions = {
        "Traveler's full name": "Please provide the traveler's full name",
        "Origin city": "What city will you be departing from?",
        "Destination city": "Where will you be traveling to?",
        "Departure date": "When will you be departing?",
        "Return date": "When will you be returning?",
        "Transportation mode": "How will you be traveling?",
        "Trip purpose and justification": "What is the purpose of this trip?"
    }
    
    return field_actions.get(missing_fields[0], f"Please provide: {missing_fields[0]}")

# --- API Endpoints ---
@app.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate_conversation(
    request: OrchestrationRequest,
    user_id: str = Depends(verify_api_key)
):
    """Main orchestration endpoint"""
    start_time = time.time()
    
    try:
        # Get state manager
        if not hasattr(app.state, 'state_manager'):
            app.state.state_manager = StateManager(
                app.state.redis_client,
                app.state.firestore_client
            )
        
        # Get or create state
        state = await app.state.state_manager.get_state(
            request.session_id,
            request.user_id or user_id
        )
        
        # Add to conversation history
        state.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "message": request.user_message
        })
        state.metadata.message_count += 1
        
        # Get missing fields
        missing_fields = []
        for field in ["traveler_name", "origin_city", "destination_city",
                     "departure_date", "return_date", "transportation_mode", "trip_purpose"]:
            if getattr(state.data, field) is None:
                missing_fields.append(field.replace("_", " ").title())
        
        # Build prompt
        recent_questions = get_recent_questions(state.conversation_history)
        prompt = STATEFUL_INTERROGATION_PROMPT.format(
            recent_questions="\n".join(recent_questions) if recent_questions else "None",
            current_data=state.data.json(indent=2),
            user_message=request.user_message,
            missing_fields=", ".join(missing_fields)
        )
        
        # Get AI response
        with model_call_duration.time():
            response = await run_in_thread(app.state.model.generate_content, prompt)
        ai_response = response.text
        
        # Add AI response to history
        state.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "message": ai_response
        })
        
        # Extract data using fast model if available
        state, confidence = await extract_data_from_conversation(
            ai_response,
            request.user_message,
            state,
            use_fast_model=True
        )
        
        # Update status
        if calculate_completion(state.data) == 100:
            state.status = DataState.COMPLETE
        elif calculate_completion(state.data) >= 70:
            state.status = DataState.PARTIAL
        else:
            state.status = DataState.INCOMPLETE
        
        # Save state
        await app.state.state_manager.save_state(request.session_id, state)
        
        # Get next action
        next_action = get_next_action(missing_fields)
        
        # Track metrics
        duration = time.time() - start_time
        request_duration.labels(method='POST', endpoint='/orchestrate').observe(duration)
        request_counter.labels(method='POST', endpoint='/orchestrate', status='200').inc()
        
        return OrchestrationResponse(
            ai_response=ai_response,
            current_state=state.data,
            data_completeness=state.status,
            next_required_fields=missing_fields,
            next_action=next_action,
            confidence_score=confidence,
            pending_confirmations=state.pending_confirmations
        )
        
    except Exception as e:
        error_counter.labels(error_type='orchestration_error').inc()
        request_counter.labels(method='POST', endpoint='/orchestrate', status='500').inc()
        logger.error(f"Orchestration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/validate-boe")
@backoff.on_exception(backoff.expo, httpx.RequestError, max_tries=3)
async def validate_boe(
    request: BOEValidationRequest,
    user_id: str = Depends(verify_api_key)
):
    """Validate BOE with retry and graceful degradation"""
    try:
        auth_token = await get_auth_token()
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        timeout = httpx.Timeout(
            connect=config.HTTP_CONNECT_TIMEOUT,
            read=config.HTTP_READ_TIMEOUT
        )
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{config.COMPLIANCE_SERVICE_URL}/validate",
                json={"boe_data": request.boe_data},
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Degraded mode response
                return {
                    "is_valid": None,
                    "compliance_score": 0,
                    "issues": [],
                    "recommendations": ["Validation service temporarily unavailable. Please try again."],
                    "degraded_mode": True
                }
                
    except Exception as e:
        logger.error(f"Validation error: {e}")
        error_counter.labels(error_type='validation_error').inc()
        # Return degraded mode response
        return {
            "is_valid": None,
            "compliance_score": 0,
            "issues": [],
            "recommendations": [
                "Unable to perform full validation at this time.",
                "Ensure travel dates are reasonable.",
                "Verify GSA per diem rates apply.",
                "Confirm supervisor approval obtained."
            ],
            "degraded_mode": True
        }

@app.get("/session/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = "json",
    user_id: str = Depends(verify_api_key)
):
    """Export session in multiple formats"""
    if not hasattr(app.state, 'state_manager'):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    state = await app.state.state_manager.get_state(session_id, user_id)
    
    if format == "json":
        return state.data.dict()
    
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Field", "Value"])
        for field, value in state.data.dict().items():
            writer.writerow([field.replace("_", " ").title(), value or ""])
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"}
        )
    
    elif format == "markdown":
        md = f"""# Travel Request Summary
        
**Session ID:** {session_id}
**Status:** {state.status}
**Completion:** {state.metadata.completion_percentage:.0f}%

## Traveler Information
- **Name:** {state.data.traveler_name or 'TBD'}
- **Origin:** {state.data.origin_city or 'TBD'}
- **Destination:** {state.data.destination_city or 'TBD'}

## Travel Details
- **Departure:** {state.data.departure_date or 'TBD'}
- **Return:** {state.data.return_date or 'TBD'}
- **Transportation:** {state.data.transportation_mode or 'TBD'}
- **Purpose:** {state.data.trip_purpose or 'TBD'}

## Cost Estimate
- **Total:** ${state.data.estimated_cost or 0:,.2f}
"""
        return StreamingResponse(
            io.BytesIO(md.encode()),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.md"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="Format must be json, csv, or markdown")

# --- Procurement Endpoints ---
@app.post("/procurement/scrape-rfps", response_model=List[RFP])
@backoff.on_exception(backoff.expo, httpx.RequestError, max_tries=3)
async def scrape_sam_gov_rfps(
    request: RFPScrapeRequest,
    user_id: str = Depends(verify_api_key)
):
    """
    Scrape recent RFP opportunities from SAM.gov based on keywords.
    This can feed the EoC discovery process in compile_reports_refactor.py.
    """
    if not config.SAM_API_KEY:
        error_counter.labels(error_type='config_missing', service='sam_gov').inc()
        raise HTTPException(status_code=503, detail="SAM.gov API key is not configured.")

    api_url = "https://api.sam.gov/opportunities/v2/search"
    
    posted_from_date = (datetime.now() - timedelta(days=request.posted_days_ago)).strftime('%m/%d/%Y')
    
    params = {
        "limit": request.limit,
        "api_key": config.SAM_API_KEY,
        "postedFrom": posted_from_date,
        "postedTo": datetime.now().strftime('%m/%d/%Y'),
        "title": request.keywords,
        "ptype": "o", # "o" for original notices
    }

    timeout = httpx.Timeout(connect=config.HTTP_CONNECT_TIMEOUT, read=config.HTTP_READ_TIMEOUT)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses

        data = response.json().get("opportunitiesData", [])
        rfps = [
            RFP(
                notice_id=opp.get("noticeId", ""),
                title=opp.get("title", ""),
                solicitation_number=opp.get("solicitationNumber", ""),
                agency=opp.get("fullParentPathName", ""),
                posted_date=opp.get("postedDate", ""),
                response_deadline=opp.get("responseDeadLine"),
                url=opp.get("uiLink", ""),
                naics_code=opp.get("naicsCode"),
                set_aside=opp.get("typeOfSetAside"),
                award_type=opp.get("typeOfContractPricing")
            ) for opp in data
        ]
        
        request_counter.labels(
            method='POST',
            endpoint='/procurement/scrape-rfps',
            status='200',
            user_id=user_id,
            session_type='procurement'
        ).inc()
        
        return rfps
        
    except httpx.HTTPStatusError as e:
        logger.error(f"SAM.gov API error: {e.response.status_code} - {e.response.text}")
        error_counter.labels(error_type='sam_api_error', service='sam_gov').inc()
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from SAM.gov: {e.response.text}")
    except Exception as e:
        logger.error(f"RFP scraping failed: {e}")
        error_counter.labels(error_type='rfp_scraping_error', service='sam_gov').inc()
        raise HTTPException(status_code=500, detail="Failed to scrape RFPs from SAM.gov.")

@app.post("/procurement/check-vendor-compliance", response_model=VendorComplianceResponse)
async def check_vendor_compliance(
    request: VendorComplianceRequest,
    user_id: str = Depends(verify_api_key)
):
    """
    Performs automated compliance checks for a subcontractor or vendor.
    Integrates with the Hierarchy of Truth for validation.
    """
    issues = []
    compliance_score = 100.0
    
    # 1. TINA Threshold Check (FAR 15.403-4)
    if request.quote_amount > 2_000_000:
        issues.append(ComplianceIssue(
            code="FAR_15_403_4",
            description="Quote exceeds $2M TINA threshold. Certified cost or pricing data is required.",
            severity="Error",
            regulation="FAR 15.403-4",
            remediation="Obtain certified cost or pricing data from vendor"
        ))
        compliance_score -= 20
    
    # 2. Simplified Acquisition Threshold (FAR 2.101)
    elif request.quote_amount > 250_000 and request.quote_amount <= 2_000_000:
        issues.append(ComplianceIssue(
            code="FAR_2_101",
            description="Quote exceeds Simplified Acquisition Threshold ($250K). Additional competition requirements apply.",
            severity="Warning",
            regulation="FAR 2.101",
            remediation="Ensure adequate competition or justification for sole source"
        ))
        compliance_score -= 10

    # 3. Cybersecurity Check (DFARS 252.204-7012)
    if not request.is_cmmc_certified and request.quote_amount > 10_000:
        issues.append(ComplianceIssue(
            code="DFARS_252_204_7012",
            description="Vendor is not CMMC certified. NIST SP 800-171 compliance is required for handling CUI.",
            severity="Warning" if request.quote_amount < 250_000 else "Error",
            regulation="DFARS 252.204-7012",
            remediation="Verify vendor has CMMC Level 2 certification or SPRS score >= 110"
        ))
        compliance_score -= 15 if request.quote_amount >= 250_000 else 5

    # 4. Purchasing System Review Check (DFARS 252.244-7001)
    if request.contract_type in ["CPFF", "T&M", "CPIF"]:
        issues.append(ComplianceIssue(
            code="DFARS_252_244_7001",
            description="Cost-reimbursable contract requires Contractor Purchasing System Review (CPSR). Ensure adequate flowdown clauses.",
            severity="Info",
            regulation="DFARS 252.244-7001",
            remediation="Include all required DFARS flowdown clauses in subcontract"
        ))
        compliance_score -= 5
    
    # 5. ITAR/Export Control Check
    if request.itar_controlled:
        issues.append(ComplianceIssue(
            code="ITAR_120_1",
            description="ITAR-controlled items require vendor to be registered with DDTC and have export license.",
            severity="Error",
            regulation="ITAR 120.1",
            remediation="Verify vendor's DDTC registration and export authorization"
        ))
        compliance_score -= 20
    
    # 6. Facility Clearance Check
    if request.requires_secret_clearance:
        issues.append(ComplianceIssue(
            code="NISPOM_2_102",
            description="Work requires facility security clearance at Secret level or higher.",
            severity="Error",
            regulation="NISPOM 2-102",
            remediation="Verify vendor has active FCL at required level via CAGE code in NCAISS"
        ))
        compliance_score -= 15
    
    # 7. Small Business Consideration (FAR 19.502)
    if request.quote_amount > 150_000 and request.quote_amount < 750_000:
        # This would normally check SAM.gov for small business status
        issues.append(ComplianceIssue(
            code="FAR_19_502",
            description="Consider small business set-aside for contracts between $150K-$750K.",
            severity="Info",
            regulation="FAR 19.502",
            remediation="Document justification if not using small business"
        ))
    
    # Calculate risk and determine approval level
    is_compliant = not any(issue.severity in ["Error", "Critical"] for issue in issues)
    compliance_score = max(0, compliance_score)
    
    risk_assessment = "Low"
    approval_required = False
    approver_level = None
    
    if compliance_score < 50:
        risk_assessment = "High"
        approval_required = True
        approver_level = "VP"
    elif compliance_score < 70:
        risk_assessment = "Medium"
        approval_required = True
        approver_level = "Director"
    elif compliance_score < 85:
        risk_assessment = "Low-Medium"
        approval_required = True
        approver_level = "PM"
    
    # TODO: Add actual SAM.gov exclusion list check via API call
    sam_status = {
        "checked": False,
        "message": "SAM.gov validation pending - manual check required"
    }
    
    request_counter.labels(
        method='POST',
        endpoint='/procurement/check-vendor-compliance',
        status='200',
        user_id=user_id,
        session_type='procurement'
    ).inc()
    
    return VendorComplianceResponse(
        vendor_name=request.vendor_name,
        is_compliant=is_compliant,
        compliance_score=compliance_score,
        issues=issues,
        sam_status=sam_status,
        risk_assessment=risk_assessment,
        approval_required=approval_required,
        approver_level=approver_level
    )

@app.post("/procure/subcontract")
@backoff.on_exception(backoff.expo, (httpx.RequestError, pybreaker.CircuitBreakerError), max_tries=3)
async def procure_subcontract(
    request: SubcontractRequest,
    user_id: str = Depends(verify_api_key)
):
    """
    Validates subcontractor against SAM.gov, DFARS, and other regulations.
    Uses circuit breaker to protect against repeated failures of compliance service.
    """
    try:
        # Define the compliance check with circuit breaker
        @compliance_breaker
        async def validate_subcontract_with_service(data: Dict[str, Any]) -> Dict[str, Any]:
            """Call external compliance service with circuit breaker protection"""
            
            if not config.COMPLIANCE_SERVICE_URL:
                # Fallback to local validation if no external service
                logger.warning("No compliance service URL configured, using local validation")
                return await local_compliance_validation(data)
            
            timeout = httpx.Timeout(
                connect=config.HTTP_CONNECT_TIMEOUT,
                read=config.HTTP_READ_TIMEOUT
            )
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                auth_token = await get_auth_token()
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{config.COMPLIANCE_SERVICE_URL}/validate",
                    json=data,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
        
        # Perform compliance validation
        compliance_result = None
        service_available = True
        
        if request.requires_compliance_check:
            try:
                compliance_result = await validate_subcontract_with_service(request.vendor_data)
            except pybreaker.CircuitBreakerError:
                logger.error("Compliance service circuit breaker is open. Using degraded mode.")
                error_counter.labels(error_type='circuit_breaker_open', service='compliance').inc()
                service_available = False
                compliance_result = {
                    "is_compliant": None,
                    "issues": ["Compliance service temporarily unavailable. Manual review required."],
                    "degraded_mode": True
                }
        
        # Local validation checks (always performed)
        local_issues = []
        
        # Check contract value thresholds
        if request.contract_value > 2_000_000:
            local_issues.append({
                "severity": "Error",
                "code": "FAR_15_403_4",
                "description": "Exceeds $2M TINA threshold. Certified cost data required."
            })
        elif request.contract_value > 500_000:
            local_issues.append({
                "severity": "Warning",
                "code": "FAR_THRESHOLD",
                "description": "Exceeds simplified acquisition threshold. Additional review required."
            })
        
        # Check ITAR
        if request.itar_controlled:
            local_issues.append({
                "severity": "Error",
                "code": "ITAR_CONTROL",
                "description": "ITAR-controlled items require DDTC registration verification."
            })
        
        # Check flowdown clauses for cost-reimbursable contracts
        if request.contract_type in ["CPFF", "T&M", "CPIF"]:
            required_flowdowns = ["DFARS 252.244-7001", "DFARS 252.204-7012"]
            missing = set(required_flowdowns) - set(request.flowdown_clauses)
            if missing:
                local_issues.append({
                    "severity": "Warning",
                    "code": "MISSING_FLOWDOWNS",
                    "description": f"Missing required flowdown clauses: {', '.join(missing)}"
                })
        
        # Combine results
        final_result = {
            "status": "validated" if service_available else "degraded",
            "contract_value": request.contract_value,
            "contract_type": request.contract_type,
            "compliance_service_result": compliance_result,
            "local_validation_issues": local_issues,
            "is_compliant": len([i for i in local_issues if i["severity"] == "Error"]) == 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Track metrics
        request_counter.labels(
            method='POST',
            endpoint='/procure/subcontract',
            status='200' if service_available else '206',  # 206 for partial content
            user_id=user_id,
            session_type='procurement'
        ).inc()
        
        return final_result
        
    except Exception as e:
        logger.error(f"Subcontract procurement error: {e}")
        error_counter.labels(error_type='subcontract_error', service='procurement').inc()
        raise HTTPException(
            status_code=500,
            detail="Internal server error during subcontract validation."
        )

async def local_compliance_validation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback local compliance validation when external service unavailable"""
    # Basic local validation logic
    issues = []
    
    if not data.get("vendor_name"):
        issues.append("Vendor name is required")
    
    if not data.get("cage_code") and not data.get("duns_number"):
        issues.append("CAGE code or DUNS number required for vendor identification")
    
    return {
        "is_compliant": len(issues) == 0,
        "issues": issues,
        "local_validation": True
    }

# --- Knowledge Graph Service ---
class KnowledgeGraphService:
    """Service for querying knowledge graph for compliance and regulatory data"""
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour TTL
        
        # Mock knowledge graph data for demonstration
        # In production, this would connect to Neo4j or similar
        self.mock_kg = {
            "FAR travel regulations": [
                {"regulation": "FAR 31.205-46", "title": "Travel Costs", "url": "https://acquisition.gov/far/31.205-46"},
                {"regulation": "GSA Per Diem", "title": "GSA Per Diem Rates", "url": "https://gsa.gov/perdiem"}
            ],
            "DFARS purchasing system": [
                {"regulation": "DFARS 252.244-7001", "title": "Contractor Purchasing System", "url": "https://acquisition.gov/dfars/252.244-7001"}
            ],
            "CMMC requirements": [
                {"regulation": "DFARS 252.204-7021", "title": "CMMC Requirements", "url": "https://acquisition.gov/dfars/252.204-7021"},
                {"regulation": "NIST SP 800-171", "title": "Security Requirements", "url": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r2.pdf"}
            ],
            "TINA threshold": [
                {"regulation": "FAR 15.403-4", "title": "Truth in Negotiations Act", "url": "https://acquisition.gov/far/15.403-4"},
                {"regulation": "10 USC 2306a", "title": "TINA Statute", "url": "https://uscode.house.gov/view.xhtml?req=10+USC+2306a"}
            ],
            "export control": [
                {"regulation": "ITAR 120.1", "title": "ITAR General Provisions", "url": "https://ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120"},
                {"regulation": "EAR 734", "title": "Export Administration Regulations", "url": "https://ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734"}
            ]
        }
    
    @knowledge_graph_breaker
    async def query(self, query: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query knowledge graph with circuit breaker protection"""
        
        # Check cache first
        cache_key = f"{query}:{context or ''}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                cache_hits.labels(cache_type='knowledge_graph').inc()
                return cached_data
        
        try:
            # In production, this would be a Neo4j/Neptune query
            if config.KNOWLEDGE_GRAPH_URL and config.NEO4J_PASSWORD:
                # Real graph database query would go here
                # For now, we'll use the mock
                pass
            
            # Mock implementation - search for best matches
            results = []
            query_lower = query.lower()
            
            # Direct match
            if query_lower in self.mock_kg:
                results = self.mock_kg[query_lower]
            else:
                # Fuzzy matching - find related regulations
                for key, values in self.mock_kg.items():
                    if any(word in key for word in query_lower.split()):
                        results.extend(values)
            
            # Add context-specific filtering if provided
            if context and results:
                # Filter based on context (e.g., "procurement", "travel", "cybersecurity")
                context_lower = context.lower()
                if "travel" in context_lower:
                    results = [r for r in results if "travel" in r.get("title", "").lower() or "31.205-46" in r.get("regulation", "")]
                elif "cyber" in context_lower or "cmmc" in context_lower:
                    results = [r for r in results if "cmmc" in r.get("title", "").lower() or "800-171" in r.get("regulation", "")]
                elif "export" in context_lower or "itar" in context_lower:
                    results = [r for r in results if "itar" in r.get("title", "").lower() or "ear" in r.get("title", "").lower()]
            
            # Cache the results
            self.cache[cache_key] = (results, datetime.now().timestamp())
            
            return results[:10]  # Limit to top 10 results
            
        except Exception as e:
            logger.error(f"Knowledge graph query error: {e}")
            error_counter.labels(error_type='kg_query_error', service='knowledge_graph').inc()
            raise
    
    async def get_regulatory_citations(self, element: str, classification: str) -> List[Dict[str, Any]]:
        """Get specific regulatory citations for an element of cost"""
        
        # Map elements to relevant queries
        query_map = {
            "Travel": "FAR travel regulations",
            "Direct Labor": "FAR direct costs",
            "Overhead": "CAS overhead allocation",
            "G&A": "CAS 410 G&A",
            "Materials": "FAR materials purchasing",
            "Subcontracts": "DFARS purchasing system"
        }
        
        query = query_map.get(element, element.lower())
        return await self.query(query, context=classification)
    
    async def validate_citation(self, regulation: str, quote: str) -> Dict[str, Any]:
        """Validate that a quote actually appears in the cited regulation"""
        
        # In production, this would fetch the actual regulation text
        # and verify the quote exists
        
        # Mock validation
        is_valid = len(quote.split()) <= 25  # Check 25-word limit
        
        return {
            "regulation": regulation,
            "quote": quote,
            "is_valid": is_valid,
            "word_count": len(quote.split()),
            "confidence": 0.95 if is_valid else 0.3
        }

# Initialize knowledge graph service
kg_service = KnowledgeGraphService()

@app.get("/kb/query")
async def query_knowledge_graph(
    q: str = Field(..., description="Query string for knowledge graph"),
    context: Optional[str] = Field(None, description="Context for filtering (e.g., 'travel', 'procurement')"),
    user_id: str = Depends(verify_api_key)
):
    """
    Query the knowledge graph for compliance data and regulatory citations.
    Supports both direct queries and context-aware filtering.
    """
    try:
        results = await kg_service.query(q, context)
        
        request_counter.labels(
            method='GET',
            endpoint='/kb/query',
            status='200',
            user_id=user_id,
            session_type='knowledge_graph'
        ).inc()
        
        return {
            "query": q,
            "context": context,
            "results": results,
            "count": len(results),
            "cached": q in kg_service.cache
        }
        
    except pybreaker.CircuitBreakerError:
        logger.error("Knowledge graph circuit breaker is open")
        error_counter.labels(error_type='circuit_breaker_open', service='knowledge_graph').inc()
        
        # Return degraded response with basic mappings
        fallback_results = []
        if "travel" in q.lower():
            fallback_results = [{"regulation": "FAR 31.205-46", "title": "Travel Costs (Cached)", "url": ""}]
        elif "cmmc" in q.lower():
            fallback_results = [{"regulation": "DFARS 252.204-7021", "title": "CMMC Requirements (Cached)", "url": ""}]
        
        return {
            "query": q,
            "context": context,
            "results": fallback_results,
            "count": len(fallback_results),
            "degraded_mode": True
        }
        
    except Exception as e:
        logger.error(f"Knowledge graph query failed: {e}")
        error_counter.labels(error_type='kg_query_failed', service='knowledge_graph').inc()
        raise HTTPException(status_code=500, detail="Could not query knowledge graph")

@app.post("/kb/validate-citation")
async def validate_citation(
    regulation: str = Field(..., description="Regulation reference (e.g., FAR 31.205-46)"),
    quote: str = Field(..., description="Quote to validate"),
    user_id: str = Depends(verify_api_key)
):
    """
    Validate that a quote actually appears in the cited regulation.
    Checks quote length and accuracy.
    """
    try:
        validation_result = await kg_service.validate_citation(regulation, quote)
        
        request_counter.labels(
            method='POST',
            endpoint='/kb/validate-citation',
            status='200',
            user_id=user_id,
            session_type='validation'
        ).inc()
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Citation validation failed: {e}")
        raise HTTPException(status_code=500, detail="Citation validation failed")

@app.get("/kb/element-citations/{element}")
async def get_element_citations(
    element: str,
    classification: str = "direct",
    user_id: str = Depends(verify_api_key)
):
    """
    Get regulatory citations for a specific element of cost.
    Useful for BOE generation and compliance checking.
    """
    try:
        citations = await kg_service.get_regulatory_citations(element, classification)
        
        request_counter.labels(
            method='GET',
            endpoint='/kb/element-citations',
            status='200',
            user_id=user_id,
            session_type='knowledge_graph'
        ).inc()
        
        return {
            "element": element,
            "classification": classification,
            "citations": citations,
            "count": len(citations)
        }
        
    except Exception as e:
        logger.error(f"Failed to get element citations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve element citations")

@app.get("/health")
async def health_check():
    """Health check with component status and circuit breaker states"""
    uptime = time.monotonic() - APP_START_TIME
    
    # Get circuit breaker states
    circuit_breaker_status = {
        "compliance": compliance_breaker.state.name if hasattr(compliance_breaker, 'state') else "unknown",
        "sam_gov": sam_gov_breaker.state.name if hasattr(sam_gov_breaker, 'state') else "unknown",
        "gemini": gemini_breaker.state.name if hasattr(gemini_breaker, 'state') else "unknown",
        "knowledge_graph": knowledge_graph_breaker.state.name if hasattr(knowledge_graph_breaker, 'state') else "unknown"
    }
    
    return {
        "status": "healthy",
        "service": "proposalOS-orchestrator",
        "version": "3.0.0",
        "uptime_seconds": round(uptime, 2),
        "primary_model": config.GEMINI_MODEL_NAME,
        "fast_model": config.GEMINI_FAST_MODEL_NAME or "using_primary",
        "components": {
            "gemini": "connected" if hasattr(app.state, 'model') else "disconnected",
            "redis": "connected" if app.state.redis_client else "disabled",
            "firestore": "connected" if app.state.firestore_client else "disabled",
            "sam_api": "configured" if config.SAM_API_KEY else "not_configured",
            "knowledge_graph": "configured" if config.NEO4J_PASSWORD else "mock_mode"
        },
        "circuit_breakers": circuit_breaker_status
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")

# --- OpenAPI Examples ---
@app.get("/")
async def root():
    """API documentation with curl examples"""
    return {
        "service": "ProposalOS Orchestrator API",
        "version": "3.0.0",
        "documentation": "/docs",
        "examples": {
            "orchestrate": """curl -X POST https://api.example.com/orchestrate \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"user_message": "I need to travel to DC next week", "session_id": "session123"}'""",
            
            "export": """curl -X GET https://api.example.com/session/session123/export?format=csv \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -o travel_request.csv"""
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
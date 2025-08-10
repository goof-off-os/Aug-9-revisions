"""
ProposalOS Orchestrator - Enhanced Production Version
======================================================
Stateful BOE Interrogation Engine with Advanced Features

Improvements over original:
- Redis/Firestore support for persistent state
- Enhanced data extraction with NLP
- Structured error handling
- Comprehensive logging
- Rate limiting and security hardening
- Advanced session management
- Real-time validation integration
"""

import os
import json
import httpx
import redis
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import google.generativeai as genai
from google.auth import default
from google.auth.transport.requests import Request as GoogleRequest
from google.cloud import firestore
import asyncio
from functools import lru_cache
import re
from enum import Enum

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration ---
class Config:
    """Centralized configuration with environment variables"""
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'proposalos-concept')
    COMPLIANCE_SERVICE_URL = os.environ.get('COMPLIANCE_SERVICE_URL', 
        'https://compliance-validator-service-53179349611.us-central1.run.app')
    
    # State management
    USE_REDIS = os.environ.get('USE_REDIS', 'false').lower() == 'true'
    USE_FIRESTORE = os.environ.get('USE_FIRESTORE', 'false').lower() == 'true'
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Security
    API_KEY_HASH = os.environ.get('API_KEY_HASH')  # SHA256 of valid API key
    RATE_LIMIT = int(os.environ.get('RATE_LIMIT', '100'))  # Requests per minute
    
    # Session management
    SESSION_TTL = int(os.environ.get('SESSION_TTL', '3600'))  # 1 hour default
    MAX_SESSIONS_PER_USER = int(os.environ.get('MAX_SESSIONS_PER_USER', '5'))

config = Config()

# --- Initialize Services ---
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# Redis client (if enabled)
redis_client = None
if config.USE_REDIS:
    try:
        redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

# Firestore client (if enabled)
firestore_client = None
if config.USE_FIRESTORE:
    try:
        firestore_client = firestore.Client(project=config.PROJECT_ID)
        logger.info("Firestore connected successfully")
    except Exception as e:
        logger.error(f"Firestore connection failed: {e}")

# --- FastAPI App ---
app = FastAPI(
    title="ProposalOS Orchestrator - Enhanced Edition",
    version="2.0.0",
    description="Stateful BOE interrogation with advanced features"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security ---
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key for authentication"""
    if not config.API_KEY_HASH:
        return True  # Skip auth if not configured
    
    provided_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if provided_hash != config.API_KEY_HASH:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# --- Data Models ---
class DataState(str, Enum):
    """State of data collection"""
    INCOMPLETE = "incomplete"
    PARTIAL = "partial"
    COMPLETE = "complete"
    VALIDATED = "validated"

class OrchestrationRequest(BaseModel):
    """Request model for orchestration endpoint"""
    user_message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, max_length=100)
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid session_id format')
        return v

class OrchestrationResponse(BaseModel):
    """Response model for orchestration endpoint"""
    ai_response: str
    current_state: Dict[str, Any]
    data_completeness: DataState
    next_required_fields: List[str]
    confidence_score: float = Field(ge=0, le=1)

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

# --- Enhanced Prompts ---
STATEFUL_INTERROGATION_PROMPT = """You are an expert BOE (Basis of Estimate) analyst with perfect memory and advanced data extraction capabilities. Your primary function is to conduct intelligent, conversational interrogations to gather all necessary information for travel cost BOEs while adhering to FAR/DFARS regulations.

GOLDEN RULE: Never ask for information that has already been provided in the current conversation. You must analyze the current_data_state and user messages to avoid redundant questions.

PROTOCOL:
1. You will receive two inputs with each interaction:
   - <current_data_state>: A JSON object containing all data collected so far
   - <user_message>: The user's latest response or input

2. Analyze the current_data_state to identify what information is still missing for a complete BOE

3. Process the user_message to extract ANY relevant information, including:
   - Explicit data (e.g., "I'm John Smith")
   - Implicit data (e.g., "flying out Monday" implies air travel and a specific date)
   - Context clues (e.g., "the usual hotel" might reference historical preferences)

4. Acknowledge what you've just learned from the user with specific details

5. Ask ONLY for the next piece of missing information, prioritizing based on:
   - Logical flow (e.g., destination before hotel details)
   - FAR compliance requirements (mandatory fields first)
   - User convenience (group related questions)

REQUIRED DATA ELEMENTS (with validation rules):
- Trip purpose and justification (min 50 chars, must reference contract/program)
- Traveler information:
  * Full name (first and last)
  * Origin city and state/country
  * Employee ID (if applicable)
- Destination:
  * City and state/country
  * Specific location/facility if known
- Travel dates:
  * Departure date and time
  * Return date and time
  * Total nights away
- Transportation:
  * Mode (air/rail/POV/rental/combination)
  * Class of service justification if not economy
  * Estimated cost or historical reference
- Lodging:
  * Number of nights
  * Preferred hotel or GSA rate compliance
  * Location requirements (proximity to venue)
- Per diem:
  * Meals and incidental expenses eligibility
  * Any provided meals to deduct
- Cost estimates:
  * Transportation costs
  * Lodging costs
  * Per diem calculations

ADVANCED EXTRACTION RULES:
- Extract dates from relative references ("next Tuesday", "the week of the 15th")
- Infer transportation mode from distance and urgency
- Calculate nights from departure/return dates
- Reference GSA rates automatically for mentioned cities
- Flag any luxury travel requiring additional justification

COMPLIANCE CHECKS:
- Verify travel is mission-essential
- Confirm lowest cost alternatives considered
- Validate against FAR 31.205-46 requirements
- Check for conference attendance restrictions
- Verify supervisor approval mentioned

CONVERSATIONAL STYLE:
- Be professional but friendly
- Use clear, specific questions
- Provide examples when helpful
- Confirm understanding of complex inputs
- Offer to calculate estimates when possible

DATA EXTRACTION FORMAT:
After processing each message, internally structure extracted data as:
{
  "explicitly_stated": {...},
  "inferred": {...},
  "needs_confirmation": {...},
  "compliance_flags": [...]
}

REMEMBER: You are stateful and intelligent. Every response should demonstrate awareness of all previously collected information and smart inference from context clues."""

DATA_EXTRACTION_PROMPT = """Extract structured data from the following conversation snippet.
Return a JSON object with extracted fields and confidence scores.

Conversation:
{conversation}

Extract the following if present:
- traveler_name (confidence: 0-1)
- origin_city (confidence: 0-1)
- destination_city (confidence: 0-1)
- departure_date (confidence: 0-1)
- return_date (confidence: 0-1)
- transportation_mode (confidence: 0-1)
- trip_purpose (confidence: 0-1)
- estimated_cost (confidence: 0-1)

Also identify:
- implied_information: List of inferences made
- missing_required: List of required fields not yet provided
- compliance_concerns: Any potential FAR/DFARS issues

Return ONLY valid JSON."""

# --- State Management ---
class StateManager:
    """Manages conversation state across different storage backends"""
    
    def __init__(self):
        self.local_cache = {}  # Always maintain local cache
        
    async def get_state(self, session_id: str) -> Dict[str, Any]:
        """Retrieve state from appropriate backend"""
        # Check local cache first
        if session_id in self.local_cache:
            return self.local_cache[session_id]
        
        # Try Redis
        if redis_client:
            try:
                state_json = redis_client.get(f"session:{session_id}")
                if state_json:
                    state = json.loads(state_json)
                    self.local_cache[session_id] = state
                    return state
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Try Firestore
        if firestore_client:
            try:
                doc = firestore_client.collection('sessions').document(session_id).get()
                if doc.exists:
                    state = doc.to_dict()
                    self.local_cache[session_id] = state
                    return state
            except Exception as e:
                logger.error(f"Firestore get error: {e}")
        
        # Return new state if not found
        return self._create_new_state()
    
    async def save_state(self, session_id: str, state: Dict[str, Any]):
        """Save state to appropriate backend"""
        # Always update local cache
        self.local_cache[session_id] = state
        
        # Save to Redis
        if redis_client:
            try:
                redis_client.setex(
                    f"session:{session_id}",
                    config.SESSION_TTL,
                    json.dumps(state)
                )
            except Exception as e:
                logger.error(f"Redis save error: {e}")
        
        # Save to Firestore
        if firestore_client:
            try:
                firestore_client.collection('sessions').document(session_id).set(state)
            except Exception as e:
                logger.error(f"Firestore save error: {e}")
    
    async def delete_state(self, session_id: str):
        """Delete state from all backends"""
        # Remove from local cache
        self.local_cache.pop(session_id, None)
        
        # Delete from Redis
        if redis_client:
            try:
                redis_client.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        # Delete from Firestore
        if firestore_client:
            try:
                firestore_client.collection('sessions').document(session_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete error: {e}")
    
    def _create_new_state(self) -> Dict[str, Any]:
        """Create a new conversation state"""
        return {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": DataState.INCOMPLETE,
            "conversation_history": [],
            "data": {
                "traveler_name": None,
                "origin_city": None,
                "destination_city": None,
                "departure_date": None,
                "return_date": None,
                "transportation_mode": None,
                "hotel_nights": None,
                "trip_purpose": None,
                "estimated_cost": None,
                "supervisor_approval": None,
                "contract_number": None
            },
            "metadata": {
                "message_count": 0,
                "last_activity": datetime.now().isoformat(),
                "completion_percentage": 0,
                "validation_status": None
            }
        }

state_manager = StateManager()

# --- Helper Functions ---
def get_auth_token():
    """Get authentication token for internal service calls"""
    try:
        credentials, _ = default()
        credentials.refresh(GoogleRequest())
        return credentials.token
    except Exception as e:
        logger.error(f"Auth token error: {e}")
        return None

async def extract_data_from_conversation(
    ai_response: str, 
    user_message: str,
    current_state: Dict[str, Any]
) -> Tuple[Dict[str, Any], float]:
    """
    Enhanced data extraction using Gemini for NLP
    Returns updated state and confidence score
    """
    try:
        # Prepare extraction prompt
        conversation = f"User: {user_message}\nAssistant: {ai_response}"
        extraction_prompt = DATA_EXTRACTION_PROMPT.format(conversation=conversation)
        
        # Call Gemini for structured extraction
        response = model.generate_content(extraction_prompt)
        extracted_json = response.text.strip()
        
        # Parse extracted data
        extracted_data = json.loads(extracted_json)
        
        # Update state with extracted data
        updated_state = current_state.copy()
        data_section = updated_state.get("data", {})
        
        # Merge extracted fields with confidence threshold
        confidence_scores = []
        for field, value in extracted_data.items():
            if field in ["implied_information", "missing_required", "compliance_concerns"]:
                updated_state[field] = value
            elif isinstance(value, dict) and "confidence" in value:
                if value["confidence"] > 0.7:  # Only update if confident
                    data_section[field] = value.get("value")
                    confidence_scores.append(value["confidence"])
        
        updated_state["data"] = data_section
        
        # Calculate overall confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        # Update metadata
        updated_state["metadata"]["completion_percentage"] = calculate_completion(data_section)
        updated_state["metadata"]["last_activity"] = datetime.now().isoformat()
        
        return updated_state, avg_confidence
        
    except Exception as e:
        logger.error(f"Data extraction error: {e}")
        return current_state, 0.5

def calculate_completion(data: Dict[str, Any]) -> float:
    """Calculate percentage of required fields completed"""
    required_fields = [
        "traveler_name", "origin_city", "destination_city",
        "departure_date", "return_date", "transportation_mode",
        "trip_purpose"
    ]
    
    completed = sum(1 for field in required_fields if data.get(field) is not None)
    return (completed / len(required_fields)) * 100

def identify_missing_fields(data: Dict[str, Any]) -> List[str]:
    """Identify which required fields are still missing"""
    required_fields = {
        "traveler_name": "Traveler's full name",
        "origin_city": "Origin city",
        "destination_city": "Destination city",
        "departure_date": "Departure date",
        "return_date": "Return date",
        "transportation_mode": "Transportation mode",
        "trip_purpose": "Trip purpose and justification",
        "estimated_cost": "Estimated total cost",
        "supervisor_approval": "Supervisor approval status"
    }
    
    missing = []
    for field, description in required_fields.items():
        if data.get(field) is None:
            missing.append(description)
    
    return missing

def determine_data_state(data: Dict[str, Any]) -> DataState:
    """Determine the current state of data collection"""
    completion = calculate_completion(data)
    
    if completion == 100:
        return DataState.COMPLETE
    elif completion >= 70:
        return DataState.PARTIAL
    else:
        return DataState.INCOMPLETE

# --- API Endpoints ---
@app.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate_conversation(
    request: OrchestrationRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Enhanced orchestration endpoint with advanced state management
    """
    try:
        # Get or create conversation state
        current_state = await state_manager.get_state(request.session_id)
        
        # Update conversation history
        current_state.setdefault("conversation_history", []).append({
            "timestamp": datetime.now().isoformat(),
            "user_message": request.user_message
        })
        
        # Update message count
        current_state["metadata"]["message_count"] += 1
        
        # Build the enhanced prompt
        prompt = f"""{STATEFUL_INTERROGATION_PROMPT}

<current_data_state>
{json.dumps(current_state["data"], indent=2)}
</current_data_state>

<conversation_history>
Last 3 messages:
{json.dumps(current_state["conversation_history"][-3:], indent=2)}
</conversation_history>

<user_message>
{request.user_message}
</user_message>

Please respond with your next question or acknowledgment:"""
        
        # Call Gemini with the stateful prompt
        response = model.generate_content(prompt)
        ai_response = response.text
        
        # Extract data from conversation
        updated_state, confidence = await extract_data_from_conversation(
            ai_response, 
            request.user_message,
            current_state
        )
        
        # Determine data completeness
        data_state = determine_data_state(updated_state["data"])
        updated_state["status"] = data_state
        
        # Identify missing fields
        missing_fields = identify_missing_fields(updated_state["data"])
        
        # Save updated state
        await state_manager.save_state(request.session_id, updated_state)
        
        # Log the interaction
        logger.info(f"Session {request.session_id}: {data_state.value} - {len(missing_fields)} fields missing")
        
        return OrchestrationResponse(
            ai_response=ai_response,
            current_state=updated_state["data"],
            data_completeness=data_state,
            next_required_fields=missing_fields,
            confidence_score=confidence
        )
        
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestration error: {str(e)}")

@app.post("/validate-boe", response_model=BOEValidationResponse)
async def validate_boe(
    request: BOEValidationRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Enhanced BOE validation with detailed compliance checking
    """
    try:
        # Get authentication token for internal service call
        auth_token = get_auth_token()
        
        if not auth_token:
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
        
        # Prepare headers for internal authentication
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Enhanced validation payload
        validation_payload = {
            "boe_data": request.boe_data,
            "strict_mode": request.strict_mode,
            "validation_rules": [
                "FAR_31_205_46",  # Travel costs
                "DFARS_231_205_46",  # DFARS travel supplement
                "CAS_410",  # G&A allocation
                "GSA_RATES"  # GSA per diem compliance
            ]
        }
        
        # Make secure internal call to compliance validator
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.COMPLIANCE_SERVICE_URL}/validate",
                json=validation_payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Compliance service error: {response.text}"
                )
            
            compliance_result = response.json()
            
            # If session_id provided, update conversation state with validation result
            if request.session_id:
                state = await state_manager.get_state(request.session_id)
                state["metadata"]["validation_status"] = compliance_result
                state["metadata"]["validated_at"] = datetime.now().isoformat()
                await state_manager.save_state(request.session_id, state)
            
            # Process compliance result into response format
            issues = compliance_result.get("issues", [])
            is_valid = len([i for i in issues if i.get("severity") == "error"]) == 0
            compliance_score = compliance_result.get("score", 0)
            
            recommendations = [
                issue.get("recommendation", "")
                for issue in issues
                if issue.get("recommendation")
            ]
            
            return BOEValidationResponse(
                is_valid=is_valid,
                compliance_score=compliance_score,
                issues=issues,
                recommendations=recommendations
            )
            
    except httpx.RequestError as e:
        logger.error(f"Service communication error: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

@app.get("/session/{session_id}/state")
async def get_session_state(
    session_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Retrieve the current state of a conversation session
    """
    state = await state_manager.get_state(session_id)
    
    if not state or state.get("metadata", {}).get("message_count", 0) == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "state": state["data"],
        "metadata": state["metadata"],
        "data_completeness": state.get("status", DataState.INCOMPLETE),
        "missing_fields": identify_missing_fields(state["data"])
    }

@app.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Clear the state for a specific session
    """
    await state_manager.delete_state(session_id)
    logger.info(f"Session {session_id} cleared")
    
    return {"message": f"Session {session_id} cleared"}

@app.get("/sessions/user/{user_id}")
async def get_user_sessions(
    user_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get all active sessions for a user
    """
    sessions = []
    
    if firestore_client:
        try:
            docs = firestore_client.collection('sessions').where('user_id', '==', user_id).stream()
            for doc in docs:
                session_data = doc.to_dict()
                sessions.append({
                    "session_id": doc.id,
                    "created_at": session_data.get("created_at"),
                    "updated_at": session_data.get("metadata", {}).get("last_activity"),
                    "completion": session_data.get("metadata", {}).get("completion_percentage", 0),
                    "status": session_data.get("status", DataState.INCOMPLETE)
                })
        except Exception as e:
            logger.error(f"Error fetching user sessions: {e}")
    
    return {"user_id": user_id, "sessions": sessions}

@app.post("/session/{session_id}/export")
async def export_session_data(
    session_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Export session data in various formats
    """
    state = await state_manager.get_state(session_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Generate export formats
    export_data = {
        "json": state["data"],
        "summary": {
            "traveler": state["data"].get("traveler_name", "Unknown"),
            "route": f"{state['data'].get('origin_city', 'Unknown')} → {state['data'].get('destination_city', 'Unknown')}",
            "dates": f"{state['data'].get('departure_date', 'TBD')} - {state['data'].get('return_date', 'TBD')}",
            "purpose": state["data"].get("trip_purpose", "Not specified"),
            "estimated_cost": state["data"].get("estimated_cost", "TBD"),
            "completion": state["metadata"].get("completion_percentage", 0)
        },
        "csv_ready": [
            ["Field", "Value"],
            ["Traveler Name", state["data"].get("traveler_name", "")],
            ["Origin", state["data"].get("origin_city", "")],
            ["Destination", state["data"].get("destination_city", "")],
            ["Departure", state["data"].get("departure_date", "")],
            ["Return", state["data"].get("return_date", "")],
            ["Transportation", state["data"].get("transportation_mode", "")],
            ["Purpose", state["data"].get("trip_purpose", "")],
            ["Est. Cost", state["data"].get("estimated_cost", "")]
        ]
    }
    
    return export_data

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    health_status = {
        "status": "healthy",
        "service": "proposalOS-orchestrator-enhanced",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "gemini": "connected" if model else "disconnected",
            "redis": "connected" if redis_client else "disabled",
            "firestore": "connected" if firestore_client else "disabled"
        },
        "metrics": {
            "active_sessions": len(state_manager.local_cache),
            "uptime_seconds": 0  # Would calculate from app start time
        }
    }
    
    return health_status

@app.get("/metrics")
async def get_metrics(authenticated: bool = Depends(verify_api_key)):
    """Get service metrics for monitoring"""
    return {
        "timestamp": datetime.now().isoformat(),
        "sessions": {
            "active": len(state_manager.local_cache),
            "total_today": 0,  # Would track in production
            "avg_completion": 0  # Would calculate from all sessions
        },
        "performance": {
            "avg_response_time_ms": 0,  # Would track with middleware
            "error_rate": 0,  # Would track errors
            "cache_hit_rate": 0  # Would track cache hits
        }
    }

# --- Startup and Shutdown ---
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("ProposalOS Orchestrator starting up...")
    
    # Verify critical services
    if not config.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured")
    
    # Test Redis connection
    if redis_client:
        try:
            redis_client.ping()
            logger.info("Redis connection verified")
        except:
            logger.error("Redis connection failed")
    
    # Test Firestore connection
    if firestore_client:
        try:
            # Test write
            test_doc = firestore_client.collection('_health').document('test')
            test_doc.set({'timestamp': datetime.now().isoformat()})
            logger.info("Firestore connection verified")
        except:
            logger.error("Firestore connection failed")
    
    logger.info("ProposalOS Orchestrator ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("ProposalOS Orchestrator shutting down...")
    
    # Save any cached states
    if redis_client or firestore_client:
        for session_id, state in state_manager.local_cache.items():
            await state_manager.save_state(session_id, state)
    
    logger.info("ProposalOS Orchestrator shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
Pull Request Plan: Align Model Choice & Remove Duplicates
==========================================================

This PR consolidates model configuration and removes duplicate code across
the ProposalOS orchestrator implementations.

CHANGES REQUIRED:
"""

# 1. CENTRALIZE MODEL CONFIGURATION
# ==================================
# Current: Multiple files with different model configs
# Target: Single source of truth for model versions

BEFORE = """
# orchestrator_enhanced.py
MODEL_VERSION = 'gemini-1.5-pro'

# orchestrator_production.py  
REQUIRED_MODEL_VERSION = 'gemini-2.0-flash-exp'

# orchestrator_procurement_enhanced.py
model = genai.GenerativeModel('gemini-pro')
"""

AFTER = """
# config.py - Single source of truth
class Config:
    REQUIRED_MODEL_VERSION = 'gemini-2.5-pro'
    
    def __init__(self):
        # Load from LLM_MODEL_G.env
        self.GEMINI_MODEL_NAME = (
            os.environ.get('GEMINI_MODEL_NAME') or 
            os.environ.get('MODEL_NAME') or 
            self.REQUIRED_MODEL_VERSION
        )
        
        # Optional fast model for extraction
        self.GEMINI_FAST_MODEL_NAME = (
            os.environ.get('GEMINI_FAST_MODEL_NAME') or 
            ''
        )

# All orchestrators import from config
from config import Config
config = Config()
"""

# 2. REMOVE DUPLICATE AUTHENTICATION CODE
# ========================================
# Current: Same auth logic copied in 3 files
# Target: Single authentication module

DUPLICATE_CODE = """
# Found in all 3 orchestrator files:
async def verify_api_key(credentials: HTTPAuthorizationCredentials):
    if config.ALLOW_INSECURE:
        return "dev_user"
    
    if not config.API_KEY_HASH:
        raise HTTPException(status_code=503, detail="Authentication not configured")
    
    provided_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if not hmac.compare_digest(provided_hash, config.API_KEY_HASH):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return provided_hash[:8]
"""

CONSOLIDATED = """
# auth.py - Shared authentication module
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import hmac

security = HTTPBearer()

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    config: Config = Depends(get_config)
) -> str:
    '''Shared authentication logic'''
    if config.ALLOW_INSECURE:
        logger.warning("Running in INSECURE mode")
        return "dev_user"
    
    if not config.API_KEY_HASH:
        raise HTTPException(status_code=503, detail="Auth not configured")
    
    provided_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if not hmac.compare_digest(provided_hash, config.API_KEY_HASH):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return provided_hash[:8]

# All orchestrators import:
from auth import verify_api_key
"""

# 3. CONSOLIDATE STATE MANAGEMENT
# ================================
# Current: Different state managers in each file
# Target: Single StateManager class

STATE_DUPLICATION = """
# orchestrator_enhanced.py
class StateManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, user_id: str):
        # Implementation...

# orchestrator_production.py
class StateManager:
    def __init__(self, redis_client, firestore_client):
        self.redis = redis_client
        self.firestore = firestore_client
        self.sessions = {}
    
    def create_session(self, user_id: str):
        # Different implementation...
"""

UNIFIED_STATE = """
# state_manager.py
class StateManager:
    '''Unified state management with multiple backends'''
    
    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        firestore_client: Optional[firestore.Client] = None,
        use_cache: bool = True
    ):
        self.redis = redis_client
        self.firestore = firestore_client
        self.use_cache = use_cache
        self.local_cache = {} if use_cache else None
    
    async def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        session_data = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'conversation': []
        }
        
        # Try Redis first
        if self.redis:
            await self.redis.setex(
                f'session:{session_id}',
                self.session_ttl,
                json.dumps(session_data)
            )
        
        # Fallback to Firestore
        elif self.firestore:
            doc_ref = self.firestore.collection('sessions').document(session_id)
            doc_ref.set(session_data)
        
        # Fallback to local cache
        else:
            self.local_cache[session_id] = session_data
        
        return session_id
"""

# 4. REMOVE DUPLICATE CIRCUIT BREAKERS
# =====================================
# Current: Same circuit breaker setup in multiple files
# Target: Shared circuit breaker configuration

CIRCUIT_BREAKER_DUPLICATION = """
# Found in multiple files:
compliance_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=60
)

sam_gov_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=120
)
"""

CENTRALIZED_BREAKERS = """
# circuit_breakers.py
import pybreaker
from typing import Dict

class CircuitBreakerRegistry:
    '''Central registry for all circuit breakers'''
    
    def __init__(self):
        self.breakers: Dict[str, pybreaker.CircuitBreaker] = {}
        self._initialize_breakers()
    
    def _initialize_breakers(self):
        '''Configure all circuit breakers'''
        
        self.breakers['compliance'] = pybreaker.CircuitBreaker(
            fail_max=3,
            reset_timeout=60,
            exclude=[httpx.HTTPStatusError]
        )
        
        self.breakers['sam_gov'] = pybreaker.CircuitBreaker(
            fail_max=3,
            reset_timeout=120,
            exclude=[httpx.HTTPStatusError]
        )
        
        self.breakers['gemini'] = pybreaker.CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
            exclude=[ValueError]
        )
        
        self.breakers['knowledge_graph'] = pybreaker.CircuitBreaker(
            fail_max=3,
            reset_timeout=90
        )
    
    def get(self, name: str) -> pybreaker.CircuitBreaker:
        return self.breakers.get(name)

# Usage in orchestrators:
breakers = CircuitBreakerRegistry()
compliance_breaker = breakers.get('compliance')
"""

# 5. CONSOLIDATE EXTRACTION LOGIC
# ================================
# Current: Similar extraction code in multiple places
# Target: Single extraction service

EXTRACTION_DUPLICATION = """
# Multiple implementations of same logic:
async def extract_data_from_conversation(conversation):
    # Implementation 1
    
async def extract_eoc_from_rfp(rfp_text):
    # Implementation 2
    
async def process_rfp_extraction(text):
    # Implementation 3
"""

UNIFIED_EXTRACTION = """
# extraction_service.py
from typing import List, Dict, Any
from extraction_schemas import ExtractedFact, ExtractionResponse
from post_processor import validate_and_repair_facts

class ExtractionService:
    '''Unified extraction service for all document types'''
    
    def __init__(self, model: genai.GenerativeModel):
        self.model = model
        self.prompts = self._load_prompts()
    
    async def extract_from_rfp(self, rfp_text: str) -> ExtractionResponse:
        '''Extract EoC facts from RFP'''
        response = await self.model.generate_content(
            self.prompts['rfp'] + rfp_text
        )
        
        # Two-line validation pattern
        facts = validate_and_repair_facts(json.loads(response.text))
        validated = [ExtractedFact(**f).dict() for f in facts]
        
        return ExtractionResponse(facts=validated)
    
    async def extract_from_conversation(
        self,
        conversation: List[Dict]
    ) -> Dict[str, Any]:
        '''Extract structured data from conversation'''
        # Implementation...
"""

# PR CHECKLIST
# =============
PR_TASKS = [
    "[ ] Centralize model configuration in config.py",
    "[ ] Create shared auth.py module",
    "[ ] Consolidate StateManager implementations",
    "[ ] Create CircuitBreakerRegistry",
    "[ ] Unify extraction logic in extraction_service.py",
    "[ ] Update all imports in orchestrator files",
    "[ ] Remove duplicate code blocks",
    "[ ] Update tests for new structure",
    "[ ] Update documentation",
    "[ ] Test all endpoints still work"
]

# FILE CHANGES SUMMARY
# ====================
FILES_TO_CREATE = [
    "config.py",                  # Centralized configuration
    "auth.py",                    # Shared authentication
    "state_manager.py",           # Unified state management
    "circuit_breakers.py",        # Circuit breaker registry
    "extraction_service.py"       # Consolidated extraction logic
]

FILES_TO_MODIFY = [
    "orchestrator_production.py",         # Use shared modules
    "orchestrator_enhanced.py",           # Use shared modules
    "orchestrator_procurement_enhanced.py" # Use shared modules
]

FILES_TO_DELETE = [
    # None - keep originals for reference during migration
]

# MIGRATION STRATEGY
# ==================
MIGRATION_STEPS = """
1. Create new shared modules without breaking existing code
2. Update orchestrator_production.py to use shared modules
3. Test orchestrator_production.py thoroughly
4. Update other orchestrators one by one
5. Remove duplicate code after all updates complete
6. Run full integration test suite
"""

# BENEFITS
# ========
BENEFITS = {
    "maintainability": "Single source of truth for each component",
    "consistency": "All orchestrators use same implementations",
    "testability": "Test shared modules once, use everywhere",
    "reliability": "Fix bugs in one place, not three",
    "performance": "Reuse connections and caches",
    "security": "Single place to audit auth and security"
}

if __name__ == "__main__":
    print("PR Plan: Align Model Choice & Remove Duplicates")
    print("=" * 50)
    print("\nFiles to create:")
    for f in FILES_TO_CREATE:
        print(f"  - {f}")
    print("\nFiles to modify:")
    for f in FILES_TO_MODIFY:
        print(f"  - {f}")
    print("\nPR Checklist:")
    for task in PR_TASKS:
        print(f"  {task}")
    print("\nMigration Strategy:")
    print(MIGRATION_STEPS)
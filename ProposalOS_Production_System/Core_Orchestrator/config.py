#!/usr/bin/env python3
"""
ProposalOS Centralized Configuration
=====================================
Single source of truth for all configuration across orchestrators

This module consolidates configuration from:
- orchestrator_production.py
- orchestrator_enhanced.py
- orchestrator_procurement_enhanced.py
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
import redis
from google.cloud import firestore

logger = logging.getLogger(__name__)


class Config:
    """
    Centralized configuration with validation
    Loads from environment variables and LLM_MODEL_G.env
    """
    
    # Model version - all services must use this
    REQUIRED_MODEL_VERSION = 'gemini-2.5-pro'
    
    def __init__(self):
        """Initialize configuration from environment"""
        
        # Load Gemini API key from LLM_MODEL_G.env first
        self._load_gemini_env()
        
        # ============ SECURITY CONFIGURATION ============
        self.API_KEY_HASH = os.environ.get('API_KEY_HASH')
        self.ALLOW_INSECURE = os.environ.get('ALLOW_INSECURE', 'false').lower() == 'true'
        
        # Security validation
        if not self.API_KEY_HASH and not self.ALLOW_INSECURE:
            raise ValueError(
                "API_KEY_HASH must be set or ALLOW_INSECURE=true for development. "
                "Generate hash with: echo -n 'your-api-key' | sha256sum"
            )
        
        # ============ CORS CONFIGURATION ============
        self.ALLOWED_ORIGINS = os.environ.get(
            'ALLOWED_ORIGINS', 
            'http://localhost:3000'
        ).split(',')
        self.ALLOWED_ORIGINS = [origin.strip() for origin in self.ALLOWED_ORIGINS]
        
        # Validate no wildcards in production
        if '*' in self.ALLOWED_ORIGINS and not self.ALLOW_INSECURE:
            raise ValueError("Wildcard origin (*) not allowed in production")
        
        # ============ MODEL CONFIGURATION ============
        self.GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
        
        # Model name resolution order: GEMINI_MODEL_NAME -> MODEL_NAME -> REQUIRED_MODEL_VERSION
        self.GEMINI_MODEL_NAME = (
            os.environ.get('GEMINI_MODEL_NAME') or 
            os.environ.get('MODEL_NAME') or 
            os.environ.get('MODEL_VERSION') or 
            self.REQUIRED_MODEL_VERSION
        ).strip()
        
        # Optional fast model for lightweight extraction
        self.GEMINI_FAST_MODEL_NAME = (
            os.environ.get('GEMINI_FAST_MODEL_NAME') or 
            os.environ.get('FAST_MODEL_NAME') or 
            ''
        ).strip()
        
        # Log model configuration
        if self.GEMINI_MODEL_NAME != self.REQUIRED_MODEL_VERSION:
            logger.warning(
                f"Model override detected: {self.GEMINI_MODEL_NAME} "
                f"(required: {self.REQUIRED_MODEL_VERSION})"
            )
        
        # ============ GCP CONFIGURATION ============
        self.PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'proposalos-concept')
        self.REGION = os.environ.get('GCP_REGION', 'us-central1')
        
        # ============ EXTERNAL SERVICES ============
        # Compliance Service
        self.COMPLIANCE_SERVICE_URL = os.environ.get(
            'COMPLIANCE_SERVICE_URL',
            'https://compliance-validator-service-53179349611.us-central1.run.app'
        )
        
        # SAM.gov API
        self.SAM_API_KEY = os.environ.get('SAM_API_KEY')
        self.SAM_API_URL = os.environ.get(
            'SAM_API_URL',
            'https://api.sam.gov/opportunities/v2/search'
        )
        
        # Knowledge Graph
        self.KNOWLEDGE_GRAPH_URL = os.environ.get(
            'KNOWLEDGE_GRAPH_URL', 
            'http://localhost:7474'
        )
        self.NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
        self.NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
        
        # ============ STATE MANAGEMENT ============
        self.USE_REDIS = os.environ.get('USE_REDIS', 'false').lower() == 'true'
        self.USE_FIRESTORE = os.environ.get('USE_FIRESTORE', 'false').lower() == 'true'
        self.REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        
        # ============ RATE LIMITING ============
        self.RATE_LIMIT = int(os.environ.get('RATE_LIMIT', '100'))  # Per minute
        self.RATE_LIMIT_BURST = int(os.environ.get('RATE_BURST', '200'))  # Burst capacity
        self.RATE_LIMIT_WINDOW = 60  # seconds
        
        # ============ SESSION MANAGEMENT ============
        self.SESSION_TTL = int(os.environ.get('SESSION_TTL', '3600'))  # 1 hour
        self.MAX_SESSIONS_PER_USER = int(os.environ.get('MAX_SESSIONS_PER_USER', '5'))
        self.MAX_CONVERSATION_HISTORY = int(os.environ.get('MAX_CONVERSATION_HISTORY', '50'))
        
        # ============ CIRCUIT BREAKER SETTINGS ============
        self.CIRCUIT_BREAKER_CONFIGS = {
            'compliance': {
                'fail_max': int(os.environ.get('CB_COMPLIANCE_FAILURES', '3')),
                'reset_timeout': int(os.environ.get('CB_COMPLIANCE_TIMEOUT', '60'))
            },
            'sam_gov': {
                'fail_max': int(os.environ.get('CB_SAM_FAILURES', '3')),
                'reset_timeout': int(os.environ.get('CB_SAM_TIMEOUT', '120'))
            },
            'gemini': {
                'fail_max': int(os.environ.get('CB_GEMINI_FAILURES', '5')),
                'reset_timeout': int(os.environ.get('CB_GEMINI_TIMEOUT', '60'))
            },
            'knowledge_graph': {
                'fail_max': int(os.environ.get('CB_KG_FAILURES', '3')),
                'reset_timeout': int(os.environ.get('CB_KG_TIMEOUT', '90'))
            }
        }
        
        # ============ TIMEOUTS ============
        self.HTTP_CONNECT_TIMEOUT = int(os.environ.get('HTTP_CONNECT_TIMEOUT', '5'))
        self.HTTP_READ_TIMEOUT = int(os.environ.get('HTTP_READ_TIMEOUT', '30'))
        self.MODEL_TIMEOUT = int(os.environ.get('MODEL_TIMEOUT', '60'))
        
        # ============ FEATURE FLAGS ============
        self.ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
        self.ENABLE_TRACING = os.environ.get('ENABLE_TRACING', 'false').lower() == 'true'
        self.ENABLE_AUDIT_LOG = os.environ.get('ENABLE_AUDIT_LOG', 'true').lower() == 'true'
        
        # ============ PATHS ============
        self.BASE_DIR = Path(__file__).parent.parent
        self.PROMPTS_DIR = self.BASE_DIR / 'prompts'
        self.SCHEMAS_DIR = self.BASE_DIR / 'schemas'
        self.LOGS_DIR = self.BASE_DIR / 'logs'
        
        # Create directories if they don't exist
        self.PROMPTS_DIR.mkdir(exist_ok=True)
        self.SCHEMAS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
    
    def _load_gemini_env(self):
        """Load Gemini API key from LLM_MODEL_G.env file"""
        env_file = Path(__file__).parent.parent / 'Configuration' / 'LLM_MODEL_G.env'
        
        # Try alternative locations
        if not env_file.exists():
            env_file = Path(__file__).parent.parent.parent / 'LLM_MODEL_G.env'
        if not env_file.exists():
            env_file = Path.home() / '.claude' / 'LLM_MODEL_G.env'
        
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            if key == 'GEMINI_API_KEY':
                                os.environ['GEMINI_API_KEY'] = value
                                logger.info(f"Loaded GEMINI_API_KEY from {env_file}")
                            elif key == 'GEMINI_MODEL_NAME':
                                os.environ['GEMINI_MODEL_NAME'] = value
                                logger.info(f"Loaded GEMINI_MODEL_NAME from {env_file}")
        else:
            logger.warning(
                "LLM_MODEL_G.env not found, expecting GEMINI_API_KEY in environment"
            )
    
    def validate(self) -> None:
        """
        Validate configuration at startup
        Raises ValueError if configuration is invalid
        """
        errors = []
        
        # Validate Gemini API key
        if not self.GEMINI_API_KEY:
            errors.append(
                "GEMINI_API_KEY is required. Set in LLM_MODEL_G.env or environment"
            )
        
        # Validate model version in production
        if not self.ALLOW_INSECURE:
            if self.GEMINI_MODEL_NAME != self.REQUIRED_MODEL_VERSION:
                errors.append(
                    f"Model version mismatch: got {self.GEMINI_MODEL_NAME}, "
                    f"required {self.REQUIRED_MODEL_VERSION}. "
                    f"Set ALLOW_INSECURE=true for development"
                )
        
        # Validate SAM API key if features are enabled
        if not self.SAM_API_KEY:
            logger.warning("SAM_API_KEY not set. RFP scraping will be unavailable")
        
        # Test Redis connection if enabled
        if self.USE_REDIS:
            try:
                r = redis.from_url(self.REDIS_URL)
                r.ping()
                logger.info("Redis connection verified")
            except Exception as e:
                if not self.ALLOW_INSECURE:
                    errors.append(f"Redis enabled but unreachable: {e}")
                else:
                    logger.warning(f"Redis unreachable, continuing in degraded mode: {e}")
        
        # Test Firestore connection if enabled
        if self.USE_FIRESTORE:
            try:
                client = firestore.Client(project=self.PROJECT_ID)
                # Test write
                test_doc = client.collection('_health').document('config_test')
                test_doc.set({'test': True})
                test_doc.delete()
                logger.info("Firestore connection verified")
            except Exception as e:
                if not self.ALLOW_INSECURE:
                    errors.append(f"Firestore enabled but unreachable: {e}")
                else:
                    logger.warning(f"Firestore unreachable, continuing in degraded mode: {e}")
        
        # Raise all errors if any
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
        
        # Log successful validation
        logger.info("Configuration validated successfully")
        logger.info(f"Environment: {'DEVELOPMENT' if self.ALLOW_INSECURE else 'PRODUCTION'}")
        logger.info(f"Primary model: {self.GEMINI_MODEL_NAME}")
        if self.GEMINI_FAST_MODEL_NAME:
            logger.info(f"Fast model: {self.GEMINI_FAST_MODEL_NAME}")
        logger.info(f"State backends: Redis={self.USE_REDIS}, Firestore={self.USE_FIRESTORE}")
    
    def get_connection_string(self, service: str) -> Optional[str]:
        """Get connection string for a service"""
        connections = {
            'redis': self.REDIS_URL,
            'neo4j': f"bolt://{self.NEO4J_USER}:{self.NEO4J_PASSWORD}@{self.KNOWLEDGE_GRAPH_URL}",
            'compliance': self.COMPLIANCE_SERVICE_URL,
            'sam': self.SAM_API_URL
        }
        return connections.get(service)
    
    def to_dict(self) -> dict:
        """Export configuration as dictionary (for debugging)"""
        return {
            'environment': 'DEVELOPMENT' if self.ALLOW_INSECURE else 'PRODUCTION',
            'model': {
                'primary': self.GEMINI_MODEL_NAME,
                'fast': self.GEMINI_FAST_MODEL_NAME or None,
                'required': self.REQUIRED_MODEL_VERSION
            },
            'security': {
                'auth_enabled': bool(self.API_KEY_HASH),
                'cors_origins': self.ALLOWED_ORIGINS
            },
            'state': {
                'redis': self.USE_REDIS,
                'firestore': self.USE_FIRESTORE
            },
            'rate_limit': {
                'limit': self.RATE_LIMIT,
                'burst': self.RATE_LIMIT_BURST
            },
            'features': {
                'metrics': self.ENABLE_METRICS,
                'tracing': self.ENABLE_TRACING,
                'audit': self.ENABLE_AUDIT_LOG
            }
        }


# Singleton instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get or create the configuration singleton
    
    Returns:
        Config: The configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
        _config_instance.validate()
    return _config_instance


# For backward compatibility
config = get_config()


if __name__ == "__main__":
    """Test configuration loading"""
    import json
    
    try:
        test_config = Config()
        test_config.validate()
        
        print("Configuration loaded successfully!")
        print(json.dumps(test_config.to_dict(), indent=2))
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)
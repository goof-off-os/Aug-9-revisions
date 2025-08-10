#!/usr/bin/env python3
"""
ProposalOS Authentication Module
=================================
Centralized authentication and authorization for all orchestrators

This module consolidates authentication logic from:
- orchestrator_production.py
- orchestrator_enhanced.py
- orchestrator_procurement_enhanced.py
"""

import hashlib
import hmac
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis.asyncio as redis

from config import get_config, Config

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class RateLimiter:
    """
    Token bucket rate limiter with Redis backend
    Falls back to in-memory limiting if Redis unavailable
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_buckets: Dict[str, Dict[str, Any]] = {}
        self.config = get_config()
    
    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier for rate limiting
            limit: Requests per window (default from config)
            window: Time window in seconds (default from config)
            
        Returns:
            bool: True if request is allowed
        """
        limit = limit or self.config.RATE_LIMIT
        window = window or self.config.RATE_LIMIT_WINDOW
        
        if self.redis_client:
            return await self._check_redis_limit(key, limit, window)
        else:
            return self._check_local_limit(key, limit, window)
    
    async def _check_redis_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> bool:
        """Check rate limit using Redis"""
        try:
            pipe = self.redis_client.pipeline()
            now = time.time()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, now - window)
            # Add current request
            pipe.zadd(key, {str(now): now})
            # Count requests in window
            pipe.zcount(key, now - window, now)
            # Set expiry
            pipe.expire(key, window + 1)
            
            results = await pipe.execute()
            request_count = results[2]
            
            return request_count <= limit
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open on Redis errors
            return True
    
    def _check_local_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> bool:
        """Check rate limit using local memory"""
        now = time.time()
        
        if key not in self.local_buckets:
            self.local_buckets[key] = {
                'tokens': limit,
                'last_refill': now
            }
        
        bucket = self.local_buckets[key]
        
        # Refill tokens based on time elapsed
        elapsed = now - bucket['last_refill']
        if elapsed > 0:
            refill_amount = int(elapsed * (limit / window))
            bucket['tokens'] = min(limit, bucket['tokens'] + refill_amount)
            bucket['last_refill'] = now
        
        # Check if request allowed
        if bucket['tokens'] > 0:
            bucket['tokens'] -= 1
            return True
        
        return False
    
    async def get_remaining_tokens(self, key: str) -> int:
        """Get number of remaining tokens for a key"""
        if self.redis_client:
            try:
                now = time.time()
                window = self.config.RATE_LIMIT_WINDOW
                count = await self.redis_client.zcount(
                    key,
                    now - window,
                    now
                )
                return max(0, self.config.RATE_LIMIT - count)
            except:
                return -1
        else:
            bucket = self.local_buckets.get(key, {})
            return bucket.get('tokens', self.config.RATE_LIMIT)


class AuthService:
    """
    Centralized authentication service
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        self.config = config or get_config()
        self.rate_limiter = RateLimiter(redis_client)
        self._api_key_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _get_client_identifier(self, request: Request) -> str:
        """Extract client IP address, handling proxies"""
        # Try to get real IP from proxy headers
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            return request.headers["x-real-ip"]
        elif request.client:
            return request.client.host
        else:
            return "unknown"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Create SHA256 hash of API key"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _verify_api_key_hash(self, provided_key: str) -> bool:
        """Verify API key using timing-safe comparison"""
        if not self.config.API_KEY_HASH:
            return False
        
        provided_hash = self._hash_api_key(provided_key)
        return hmac.compare_digest(provided_hash, self.config.API_KEY_HASH)
    
    async def authenticate(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None
    ) -> str:
        """
        Authenticate a request
        
        Args:
            request: FastAPI request object
            credentials: Optional bearer token credentials
            
        Returns:
            str: User identifier (truncated API key hash or 'dev_user')
            
        Raises:
            HTTPException: If authentication fails
        """
        # Development mode bypass
        if self.config.ALLOW_INSECURE:
            logger.warning("Running in INSECURE mode - authentication bypassed")
            return "dev_user"
        
        # Check for API key hash configuration
        if not self.config.API_KEY_HASH:
            raise HTTPException(
                status_code=503,
                detail="Authentication not configured"
            )
        
        # Extract API key from various sources
        api_key = None
        
        # Try Authorization header first
        if credentials and credentials.credentials:
            api_key = credentials.credentials
        # Try X-API-Key header
        elif "x-api-key" in request.headers:
            api_key = request.headers["x-api-key"]
        # Try query parameter (not recommended for production)
        elif "api_key" in request.query_params:
            api_key = request.query_params["api_key"]
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verify API key
        if not self._verify_api_key_hash(api_key):
            logger.warning(f"Invalid API key attempt from {self._get_client_identifier(request)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Generate user identifier
        user_id = self._hash_api_key(api_key)[:8]
        
        # Check rate limiting
        client_ip = self._get_client_identifier(request)
        rate_key = f"rate:{user_id}:{client_ip}"
        
        if not await self.rate_limiter.check_rate_limit(rate_key):
            remaining = await self.rate_limiter.get_remaining_tokens(rate_key)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.config.RATE_LIMIT),
                    "X-RateLimit-Remaining": str(remaining),
                    "Retry-After": str(self.config.RATE_LIMIT_WINDOW)
                }
            )
        
        return user_id
    
    async def authorize(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if user is authorized for an action
        
        Args:
            user_id: User identifier
            resource: Resource being accessed
            action: Action being performed
            
        Returns:
            bool: True if authorized
        """
        # For now, authenticated users can access everything
        # This can be extended with role-based access control
        
        # Development mode allows everything
        if user_id == "dev_user":
            return True
        
        # Add resource-specific authorization here
        # Example:
        # if resource == "admin" and user_id not in ADMIN_USERS:
        #     return False
        
        return True


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service(
    redis_client: Optional[redis.Redis] = None
) -> AuthService:
    """Get or create the authentication service singleton"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(redis_client=redis_client)
    return _auth_service


# FastAPI dependency for authentication
async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency for API key verification
    
    Args:
        request: FastAPI request
        credentials: Bearer token from Authorization header
        
    Returns:
        str: User identifier
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_service = get_auth_service()
    return await auth_service.authenticate(request, credentials)


# Optional: Dependency for specific resource authorization
def require_permission(resource: str, action: str):
    """
    Create a dependency that requires specific permissions
    
    Args:
        resource: Resource name
        action: Action name
        
    Returns:
        Dependency function
    """
    async def permission_checker(
        user_id: str = Depends(verify_api_key)
    ):
        auth_service = get_auth_service()
        if not await auth_service.authorize(user_id, resource, action):
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized for {action} on {resource}"
            )
        return user_id
    
    return permission_checker


# Middleware for adding security headers
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Remove sensitive headers
    response.headers.pop("Server", None)
    response.headers.pop("X-Powered-By", None)
    
    return response


if __name__ == "__main__":
    """Test authentication module"""
    import asyncio
    
    async def test_auth():
        # Test with development mode
        import os
        os.environ['ALLOW_INSECURE'] = 'true'
        
        auth = AuthService()
        
        # Create mock request
        class MockRequest:
            client = type('obj', (object,), {'host': '127.0.0.1'})
            headers = {}
            query_params = {}
        
        request = MockRequest()
        
        # Test authentication
        user_id = await auth.authenticate(request, None)
        print(f"Authenticated as: {user_id}")
        
        # Test authorization
        authorized = await auth.authorize(user_id, "test_resource", "read")
        print(f"Authorized: {authorized}")
        
        # Test rate limiting
        for i in range(5):
            allowed = await auth.rate_limiter.check_rate_limit(f"test:{user_id}")
            print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'}")
    
    asyncio.run(test_auth())
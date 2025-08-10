#!/usr/bin/env python3
"""
ProposalOS State Management Module
===================================
Unified state management with multiple backend support

This module consolidates state management from:
- orchestrator_production.py (Redis + Firestore)
- orchestrator_enhanced.py (In-memory)
- orchestrator_procurement_enhanced.py (Mixed)
"""

import json
import uuid
import logging
import asyncio
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from google.cloud import firestore

from config import get_config, Config

logger = logging.getLogger(__name__)


class DataState(str, Enum):
    """State of data collection in a session"""
    INCOMPLETE = "incomplete"
    PARTIAL = "partial"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class SessionData:
    """Session data structure"""
    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    data_state: DataState
    conversation: List[Dict[str, Any]]
    collected_facts: Dict[str, Any]
    pending_confirmations: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            **asdict(self),
            'data_state': self.data_state.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary"""
        data['data_state'] = DataState(data.get('data_state', 'incomplete'))
        return cls(**data)


class StateManager:
    """
    Unified state manager with multiple backend support
    Supports Redis, Firestore, and in-memory storage
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        firestore_client: Optional[firestore.Client] = None,
        config: Optional[Config] = None
    ):
        """
        Initialize state manager
        
        Args:
            redis_client: Optional Redis client for distributed state
            firestore_client: Optional Firestore client for persistent state
            config: Configuration object
        """
        self.config = config or get_config()
        self.redis = redis_client
        self.firestore = firestore_client
        
        # Local cache for performance
        self.local_cache: Dict[str, SessionData] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # User session tracking
        self.user_sessions: Dict[str, Set[str]] = {}
        
        # Session settings from config
        self.session_ttl = self.config.SESSION_TTL
        self.max_sessions_per_user = self.config.MAX_SESSIONS_PER_USER
        self.max_conversation_history = self.config.MAX_CONVERSATION_HISTORY
        
        logger.info(
            f"StateManager initialized - "
            f"Redis: {bool(self.redis)}, "
            f"Firestore: {bool(self.firestore)}, "
            f"Local cache: True"
        )
    
    async def create_session(
        self,
        user_id: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new session
        
        Args:
            user_id: User identifier
            initial_data: Optional initial session data
            
        Returns:
            str: Session ID
            
        Raises:
            ValueError: If user has too many active sessions
        """
        # Check session limit
        user_sessions = await self.get_user_sessions(user_id)
        if len(user_sessions) >= self.max_sessions_per_user:
            # Clean up old sessions
            await self.cleanup_user_sessions(user_id)
            user_sessions = await self.get_user_sessions(user_id)
            
            if len(user_sessions) >= self.max_sessions_per_user:
                raise ValueError(
                    f"User {user_id} has reached maximum session limit "
                    f"({self.max_sessions_per_user})"
                )
        
        # Create session
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            data_state=DataState.INCOMPLETE,
            conversation=[],
            collected_facts=initial_data or {},
            pending_confirmations={},
            metadata={}
        )
        
        # Store in all available backends
        await self._store_session(session_data)
        
        # Track user session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    async def get_session(
        self,
        session_id: str,
        use_cache: bool = True
    ) -> Optional[SessionData]:
        """
        Retrieve a session
        
        Args:
            session_id: Session identifier
            use_cache: Whether to use local cache
            
        Returns:
            SessionData or None if not found
        """
        # Check local cache first
        if use_cache and session_id in self.local_cache:
            session = self.local_cache[session_id]
            # Check if session is expired
            created_at = datetime.fromisoformat(session.created_at)
            if datetime.now() - created_at < timedelta(seconds=self.session_ttl):
                return session
            else:
                # Session expired, remove from cache
                del self.local_cache[session_id]
        
        # Try Redis
        if self.redis:
            try:
                data = await self.redis.get(f"session:{session_id}")
                if data:
                    session_dict = json.loads(data)
                    session = SessionData.from_dict(session_dict)
                    # Update cache
                    self.local_cache[session_id] = session
                    return session
            except Exception as e:
                logger.error(f"Redis get error for session {session_id}: {e}")
        
        # Try Firestore
        if self.firestore:
            try:
                doc_ref = self.firestore.collection('sessions').document(session_id)
                doc = doc_ref.get()
                if doc.exists:
                    session = SessionData.from_dict(doc.to_dict())
                    # Update cache and Redis
                    self.local_cache[session_id] = session
                    if self.redis:
                        await self._store_redis_session(session)
                    return session
            except Exception as e:
                logger.error(f"Firestore get error for session {session_id}: {e}")
        
        # Check local cache as last resort
        if session_id in self.local_cache:
            return self.local_cache[session_id]
        
        return None
    
    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a session
        
        Args:
            session_id: Session identifier
            updates: Dictionary of updates to apply
            
        Returns:
            bool: True if successful
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for update")
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(session, key):
                if key == 'data_state' and isinstance(value, str):
                    value = DataState(value)
                setattr(session, key, value)
        
        # Update timestamp
        session.updated_at = datetime.now().isoformat()
        
        # Trim conversation history if needed
        if len(session.conversation) > self.max_conversation_history:
            session.conversation = session.conversation[-self.max_conversation_history:]
        
        # Store updated session
        await self._store_session(session)
        
        logger.debug(f"Updated session {session_id}")
        return True
    
    async def add_to_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to session conversation
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            bool: True if successful
        """
        session = await self.get_session(session_id)
        if not session:
            return False
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        session.conversation.append(message)
        
        # Trim if exceeds limit
        if len(session.conversation) > self.max_conversation_history:
            session.conversation = session.conversation[-self.max_conversation_history:]
        
        session.updated_at = datetime.now().isoformat()
        
        await self._store_session(session)
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if successful
        """
        # Get session to find user
        session = await self.get_session(session_id)
        if session:
            # Remove from user sessions
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_id)
        
        # Delete from all backends
        deleted = False
        
        # Redis
        if self.redis:
            try:
                result = await self.redis.delete(f"session:{session_id}")
                deleted = deleted or bool(result)
            except Exception as e:
                logger.error(f"Redis delete error for session {session_id}: {e}")
        
        # Firestore
        if self.firestore:
            try:
                doc_ref = self.firestore.collection('sessions').document(session_id)
                doc_ref.delete()
                deleted = True
            except Exception as e:
                logger.error(f"Firestore delete error for session {session_id}: {e}")
        
        # Local cache
        if session_id in self.local_cache:
            del self.local_cache[session_id]
            deleted = True
        
        if deleted:
            logger.info(f"Deleted session {session_id}")
        
        return deleted
    
    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[SessionData]:
        """
        Get all sessions for a user
        
        Args:
            user_id: User identifier
            active_only: Only return active (non-expired) sessions
            
        Returns:
            List of SessionData objects
        """
        sessions = []
        
        # Try Redis first for user session list
        if self.redis:
            try:
                session_ids = await self.redis.smembers(f"user_sessions:{user_id}")
                for session_id in session_ids:
                    session = await self.get_session(session_id.decode() if isinstance(session_id, bytes) else session_id)
                    if session:
                        if not active_only or self._is_session_active(session):
                            sessions.append(session)
            except Exception as e:
                logger.error(f"Redis error getting user sessions: {e}")
        
        # Try Firestore
        elif self.firestore:
            try:
                query = self.firestore.collection('sessions').where('user_id', '==', user_id)
                docs = query.stream()
                for doc in docs:
                    session = SessionData.from_dict(doc.to_dict())
                    if not active_only or self._is_session_active(session):
                        sessions.append(session)
            except Exception as e:
                logger.error(f"Firestore error getting user sessions: {e}")
        
        # Fallback to local cache
        else:
            for session_id in self.user_sessions.get(user_id, set()):
                if session_id in self.local_cache:
                    session = self.local_cache[session_id]
                    if not active_only or self._is_session_active(session):
                        sessions.append(session)
        
        return sessions
    
    async def cleanup_user_sessions(self, user_id: str) -> int:
        """
        Clean up expired sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            int: Number of sessions cleaned up
        """
        sessions = await self.get_user_sessions(user_id, active_only=False)
        cleaned = 0
        
        for session in sessions:
            if not self._is_session_active(session):
                if await self.delete_session(session.session_id):
                    cleaned += 1
        
        if cleaned:
            logger.info(f"Cleaned up {cleaned} expired sessions for user {user_id}")
        
        return cleaned
    
    async def cleanup_all_expired(self) -> int:
        """
        Clean up all expired sessions
        
        Returns:
            int: Number of sessions cleaned up
        """
        cleaned = 0
        
        # Clean local cache
        expired_ids = []
        for session_id, session in self.local_cache.items():
            if not self._is_session_active(session):
                expired_ids.append(session_id)
        
        for session_id in expired_ids:
            if await self.delete_session(session_id):
                cleaned += 1
        
        if cleaned:
            logger.info(f"Cleaned up {cleaned} expired sessions total")
        
        return cleaned
    
    async def flush_all(self) -> None:
        """Flush all cached data to persistent storage"""
        if not self.redis and not self.firestore:
            logger.warning("No persistent storage configured, cannot flush")
            return
        
        for session in self.local_cache.values():
            await self._store_session(session, skip_cache=True)
        
        logger.info(f"Flushed {len(self.local_cache)} sessions to persistent storage")
    
    # Private helper methods
    
    async def _store_session(
        self,
        session: SessionData,
        skip_cache: bool = False
    ) -> None:
        """Store session in all available backends"""
        session_dict = session.to_dict()
        
        # Local cache
        if not skip_cache:
            self.local_cache[session.session_id] = session
        
        # Redis
        if self.redis:
            await self._store_redis_session(session)
        
        # Firestore
        if self.firestore:
            await self._store_firestore_session(session)
    
    async def _store_redis_session(self, session: SessionData) -> None:
        """Store session in Redis"""
        try:
            session_key = f"session:{session.session_id}"
            session_data = json.dumps(session.to_dict())
            
            # Store session with TTL
            await self.redis.setex(
                session_key,
                self.session_ttl,
                session_data
            )
            
            # Track user sessions
            user_key = f"user_sessions:{session.user_id}"
            await self.redis.sadd(user_key, session.session_id)
            await self.redis.expire(user_key, self.session_ttl)
            
        except Exception as e:
            logger.error(f"Redis store error for session {session.session_id}: {e}")
    
    async def _store_firestore_session(self, session: SessionData) -> None:
        """Store session in Firestore"""
        try:
            doc_ref = self.firestore.collection('sessions').document(session.session_id)
            doc_ref.set(session.to_dict())
        except Exception as e:
            logger.error(f"Firestore store error for session {session.session_id}: {e}")
    
    def _is_session_active(self, session: SessionData) -> bool:
        """Check if session is still active"""
        created_at = datetime.fromisoformat(session.created_at)
        age = datetime.now() - created_at
        return age.total_seconds() < self.session_ttl


# Singleton instance
_state_manager: Optional[StateManager] = None


def get_state_manager(
    redis_client: Optional[redis.Redis] = None,
    firestore_client: Optional[firestore.Client] = None
) -> StateManager:
    """Get or create the state manager singleton"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager(
            redis_client=redis_client,
            firestore_client=firestore_client
        )
    return _state_manager


if __name__ == "__main__":
    """Test state manager"""
    import asyncio
    
    async def test_state_manager():
        # Create state manager with local storage only
        manager = StateManager()
        
        # Create session
        session_id = await manager.create_session("test_user", {"initial": "data"})
        print(f"Created session: {session_id}")
        
        # Get session
        session = await manager.get_session(session_id)
        print(f"Retrieved session: {session.session_id}")
        
        # Update session
        await manager.update_session(session_id, {
            "data_state": "partial",
            "collected_facts": {"fact1": "value1"}
        })
        
        # Add to conversation
        await manager.add_to_conversation(
            session_id,
            "user",
            "Test message"
        )
        
        # Get updated session
        session = await manager.get_session(session_id)
        print(f"Conversation: {session.conversation}")
        
        # Get user sessions
        user_sessions = await manager.get_user_sessions("test_user")
        print(f"User sessions: {len(user_sessions)}")
        
        # Delete session
        deleted = await manager.delete_session(session_id)
        print(f"Deleted: {deleted}")
    
    asyncio.run(test_state_manager())
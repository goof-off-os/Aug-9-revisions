#!/usr/bin/env python3
"""
ProposalOS Circuit Breaker Registry
====================================
Centralized circuit breaker management for all external services

This module consolidates circuit breaker configuration from:
- orchestrator_production.py
- orchestrator_enhanced.py
- orchestrator_procurement_enhanced.py
"""

import logging
import time
from typing import Dict, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass

import pybreaker
import httpx

from config import get_config, Config

logger = logging.getLogger(__name__)


class ServiceName(str, Enum):
    """Enumeration of protected services"""
    COMPLIANCE = "compliance"
    SAM_GOV = "sam_gov"
    GEMINI = "gemini"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    REDIS = "redis"
    FIRESTORE = "firestore"
    EXTERNAL_API = "external_api"


@dataclass
class CircuitBreakerMetrics:
    """Metrics for a circuit breaker"""
    name: str
    state: str
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    expected_reset_time: Optional[float]
    
    @property
    def is_open(self) -> bool:
        return self.state == "open"
    
    @property
    def is_closed(self) -> bool:
        return self.state == "closed"
    
    @property
    def is_half_open(self) -> bool:
        return self.state == "half-open"


class MonitoredCircuitBreaker(pybreaker.CircuitBreaker):
    """
    Extended circuit breaker with monitoring capabilities
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self._metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'open_transitions': 0
        }
        
        # Add listeners for state changes
        original_on_circuit_open = kwargs.get('on_circuit_open')
        
        def on_open_wrapper(breaker, *args, **kwargs):
            self._metrics['open_transitions'] += 1
            logger.warning(f"Circuit breaker '{name}' opened after {breaker.fail_counter} failures")
            if original_on_circuit_open:
                original_on_circuit_open(breaker, *args, **kwargs)
        
        self._on_circuit_open = on_open_wrapper
    
    def call(self, func, *args, **kwargs):
        """Override call to track metrics"""
        self._metrics['total_calls'] += 1
        
        try:
            result = super().call(func, *args, **kwargs)
            self._metrics['successful_calls'] += 1
            return result
        except Exception as e:
            self._metrics['failed_calls'] += 1
            raise
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics for this breaker"""
        return CircuitBreakerMetrics(
            name=self.name,
            state=self.state.name.lower(),
            failure_count=self.fail_counter,
            success_count=self._metrics['successful_calls'],
            last_failure_time=self.last_failure if hasattr(self, 'last_failure') else None,
            expected_reset_time=self._expected_reset_time() if self.state == pybreaker.STATE_OPEN else None
        )
    
    def _expected_reset_time(self) -> Optional[float]:
        """Calculate when the breaker will attempt to reset"""
        if hasattr(self, '_opened') and self._opened:
            return self._opened + self.reset_timeout
        return None


class CircuitBreakerRegistry:
    """
    Central registry for all circuit breakers in the system
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize circuit breaker registry
        
        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        self.breakers: Dict[str, MonitoredCircuitBreaker] = {}
        self._initialize_breakers()
        
        logger.info(f"Circuit breaker registry initialized with {len(self.breakers)} breakers")
    
    def _initialize_breakers(self):
        """Configure all circuit breakers based on config"""
        
        # Get configurations from config
        breaker_configs = self.config.CIRCUIT_BREAKER_CONFIGS
        
        # Compliance Service Breaker
        self.breakers[ServiceName.COMPLIANCE] = MonitoredCircuitBreaker(
            name=ServiceName.COMPLIANCE,
            fail_max=breaker_configs['compliance']['fail_max'],
            reset_timeout=breaker_configs['compliance']['reset_timeout'],
            exclude=[httpx.HTTPStatusError],  # Don't trip on 4xx errors
            expected_exception=pybreaker.CircuitBreakerError
        )
        
        # SAM.gov API Breaker (longer recovery for government service)
        self.breakers[ServiceName.SAM_GOV] = MonitoredCircuitBreaker(
            name=ServiceName.SAM_GOV,
            fail_max=breaker_configs['sam_gov']['fail_max'],
            reset_timeout=breaker_configs['sam_gov']['reset_timeout'],
            exclude=[httpx.HTTPStatusError],
            expected_exception=pybreaker.CircuitBreakerError
        )
        
        # Gemini Model Breaker (more tolerant of failures)
        self.breakers[ServiceName.GEMINI] = MonitoredCircuitBreaker(
            name=ServiceName.GEMINI,
            fail_max=breaker_configs['gemini']['fail_max'],
            reset_timeout=breaker_configs['gemini']['reset_timeout'],
            exclude=[ValueError, KeyError],  # Don't trip on parsing errors
            expected_exception=pybreaker.CircuitBreakerError
        )
        
        # Knowledge Graph Breaker
        self.breakers[ServiceName.KNOWLEDGE_GRAPH] = MonitoredCircuitBreaker(
            name=ServiceName.KNOWLEDGE_GRAPH,
            fail_max=breaker_configs['knowledge_graph']['fail_max'],
            reset_timeout=breaker_configs['knowledge_graph']['reset_timeout'],
            exclude=[ValueError],
            expected_exception=pybreaker.CircuitBreakerError
        )
        
        # Redis Breaker (quick recovery for cache)
        self.breakers[ServiceName.REDIS] = MonitoredCircuitBreaker(
            name=ServiceName.REDIS,
            fail_max=2,
            reset_timeout=30,
            expected_exception=pybreaker.CircuitBreakerError
        )
        
        # Firestore Breaker
        self.breakers[ServiceName.FIRESTORE] = MonitoredCircuitBreaker(
            name=ServiceName.FIRESTORE,
            fail_max=3,
            reset_timeout=60,
            expected_exception=pybreaker.CircuitBreakerError
        )
        
        # Generic External API Breaker
        self.breakers[ServiceName.EXTERNAL_API] = MonitoredCircuitBreaker(
            name=ServiceName.EXTERNAL_API,
            fail_max=3,
            reset_timeout=60,
            exclude=[httpx.HTTPStatusError],
            expected_exception=pybreaker.CircuitBreakerError
        )
    
    def get(self, service: str) -> MonitoredCircuitBreaker:
        """
        Get circuit breaker for a service
        
        Args:
            service: Service name (from ServiceName enum or string)
            
        Returns:
            MonitoredCircuitBreaker instance
            
        Raises:
            KeyError: If service not found
        """
        if isinstance(service, ServiceName):
            service = service.value
        
        if service not in self.breakers:
            logger.warning(f"Unknown service '{service}', using generic external API breaker")
            return self.breakers[ServiceName.EXTERNAL_API]
        
        return self.breakers[service]
    
    def get_all_metrics(self) -> Dict[str, CircuitBreakerMetrics]:
        """
        Get metrics for all circuit breakers
        
        Returns:
            Dictionary of service name to metrics
        """
        return {
            name: breaker.get_metrics()
            for name, breaker in self.breakers.items()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of protected services
        
        Returns:
            Health status dictionary
        """
        metrics = self.get_all_metrics()
        
        open_breakers = [
            name for name, metric in metrics.items()
            if metric.is_open
        ]
        
        half_open_breakers = [
            name for name, metric in metrics.items()
            if metric.is_half_open
        ]
        
        return {
            'healthy': len(open_breakers) == 0,
            'degraded': len(open_breakers) > 0,
            'open_breakers': open_breakers,
            'half_open_breakers': half_open_breakers,
            'total_breakers': len(self.breakers),
            'metrics': {
                name: {
                    'state': metric.state,
                    'failures': metric.failure_count,
                    'successes': metric.success_count
                }
                for name, metric in metrics.items()
            }
        }
    
    def reset(self, service: str) -> bool:
        """
        Manually reset a circuit breaker
        
        Args:
            service: Service name
            
        Returns:
            bool: True if reset successful
        """
        try:
            breaker = self.get(service)
            breaker.reset()
            logger.info(f"Manually reset circuit breaker for {service}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset breaker for {service}: {e}")
            return False
    
    def reset_all(self) -> Dict[str, bool]:
        """
        Reset all circuit breakers
        
        Returns:
            Dictionary of service to reset success
        """
        results = {}
        for service in self.breakers.keys():
            results[service] = self.reset(service)
        return results


# Decorator for protected functions
def circuit_breaker(service: str):
    """
    Decorator to protect a function with a circuit breaker
    
    Args:
        service: Service name from ServiceName enum
        
    Usage:
        @circuit_breaker(ServiceName.COMPLIANCE)
        async def call_compliance_api():
            ...
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            registry = get_circuit_breaker_registry()
            breaker = registry.get(service)
            return breaker(func)(*args, **kwargs)
        return wrapper
    return decorator


# Helper function for async circuit breaking
async def with_circuit_breaker(
    service: str,
    func: Callable,
    *args,
    fallback: Optional[Any] = None,
    **kwargs
) -> Any:
    """
    Execute a function with circuit breaker protection
    
    Args:
        service: Service name
        func: Async function to execute
        *args: Function arguments
        fallback: Optional fallback value on circuit open
        **kwargs: Function keyword arguments
        
    Returns:
        Function result or fallback value
    """
    registry = get_circuit_breaker_registry()
    breaker = registry.get(service)
    
    try:
        # For async functions, we need to handle them specially
        if asyncio.iscoroutinefunction(func):
            # Create a wrapper that can be called by the breaker
            def sync_wrapper():
                return asyncio.create_task(func(*args, **kwargs))
            
            task = breaker(sync_wrapper)()
            return await task
        else:
            return breaker(func)(*args, **kwargs)
            
    except pybreaker.CircuitBreakerError:
        logger.warning(f"Circuit breaker open for {service}, using fallback")
        if fallback is not None:
            return fallback
        raise


# Singleton instance
_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get or create the circuit breaker registry singleton"""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


# Export commonly used breakers for convenience
def get_compliance_breaker() -> MonitoredCircuitBreaker:
    """Get compliance service circuit breaker"""
    return get_circuit_breaker_registry().get(ServiceName.COMPLIANCE)


def get_sam_gov_breaker() -> MonitoredCircuitBreaker:
    """Get SAM.gov API circuit breaker"""
    return get_circuit_breaker_registry().get(ServiceName.SAM_GOV)


def get_gemini_breaker() -> MonitoredCircuitBreaker:
    """Get Gemini model circuit breaker"""
    return get_circuit_breaker_registry().get(ServiceName.GEMINI)


def get_knowledge_graph_breaker() -> MonitoredCircuitBreaker:
    """Get knowledge graph circuit breaker"""
    return get_circuit_breaker_registry().get(ServiceName.KNOWLEDGE_GRAPH)


if __name__ == "__main__":
    """Test circuit breaker registry"""
    import asyncio
    
    async def test_breakers():
        # Create registry
        registry = CircuitBreakerRegistry()
        
        # Get health status
        health = registry.get_health_status()
        print(f"Initial health: {health}")
        
        # Test a breaker with failures
        compliance_breaker = registry.get(ServiceName.COMPLIANCE)
        
        def failing_function():
            raise Exception("Service unavailable")
        
        # Trigger failures
        for i in range(4):
            try:
                compliance_breaker(failing_function)()
            except Exception:
                pass
        
        # Check metrics
        metrics = compliance_breaker.get_metrics()
        print(f"Compliance breaker metrics: {metrics}")
        
        # Check health again
        health = registry.get_health_status()
        print(f"Health after failures: {health}")
        
        # Test async function with circuit breaker
        async def async_api_call():
            await asyncio.sleep(0.1)
            return "Success"
        
        result = await with_circuit_breaker(
            ServiceName.GEMINI,
            async_api_call,
            fallback="Fallback value"
        )
        print(f"Async call result: {result}")
    
    asyncio.run(test_breakers())
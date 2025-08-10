"""
ProposalOS Report Generation Engine (RGE)
==========================================
Unified report generation system for ProposalOS

This package provides:
- Unified data schemas for all report types
- Template registry for available reports
- Modular renderer system
- Validation pipeline
- FastAPI endpoints for report generation
"""

__version__ = "1.0.0"
__author__ = "ProposalOS Team"

from .schemas import UnifiedPayload, UIInputs, KBFact, Allocation
from .registry import REGISTRY, get_template

__all__ = [
    "UnifiedPayload",
    "UIInputs", 
    "KBFact",
    "Allocation",
    "REGISTRY",
    "get_template"
]
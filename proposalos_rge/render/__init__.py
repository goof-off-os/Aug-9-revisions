# proposalos_rge/render/__init__.py
"""
Report Renderer Module
======================
Modular renderers for different report formats
"""

from typing import Protocol, runtime_checkable
from ..schemas import UnifiedPayload


@runtime_checkable
class Renderer(Protocol):
    """Protocol for report renderers"""
    
    def render(self, payload: UnifiedPayload) -> str:
        """
        Render payload to output format
        
        Args:
            payload: Unified payload to render
            
        Returns:
            Rendered output as string
        """
        ...


__all__ = ["Renderer"]
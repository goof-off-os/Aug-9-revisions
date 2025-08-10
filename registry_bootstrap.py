#!/usr/bin/env python3
"""
Template Registry Bootstrap
============================
Central registry for all ProposalOS report templates and renderers.
Provides a unified interface to discover, register, and render reports.
"""

from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import importlib
import inspect
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Metadata about a registered template"""
    id: str
    name: str
    description: str
    renderer: Callable
    module_path: str
    required_fields: List[str] = field(default_factory=list)
    category: str = "General"
    format: str = "text/markdown"
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)


class TemplateRegistry:
    """
    Central registry for all report templates.
    
    Features:
    - Auto-discovery of renderers
    - Lazy loading of modules
    - Validation of required fields
    - Categorization and tagging
    - Version management
    """
    
    def __init__(self):
        self._templates: Dict[str, TemplateInfo] = {}
        self._categories: Dict[str, List[str]] = {}
        self._renderer_cache: Dict[str, Callable] = {}
        
    def register(
        self,
        template_id: str,
        name: str,
        description: str,
        renderer: Optional[Callable] = None,
        module_path: Optional[str] = None,
        function_name: Optional[str] = None,
        required_fields: Optional[List[str]] = None,
        category: str = "General",
        format: str = "text/markdown",
        version: str = "1.0.0",
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Register a template with the registry.
        
        Args:
            template_id: Unique identifier for the template
            name: Human-readable name
            description: What this template does
            renderer: Direct function reference (optional)
            module_path: Module containing the renderer (for lazy loading)
            function_name: Name of the renderer function in the module
            required_fields: List of required payload fields
            category: Template category (DFARS, FAR, Cost, etc.)
            format: Output format (text/markdown, text/html, etc.)
            version: Template version
            tags: Additional tags for searching/filtering
        """
        if template_id in self._templates:
            logger.warning(f"Template {template_id} already registered, overwriting")
        
        # If renderer not provided, we'll lazy load it
        if renderer is None and module_path and function_name:
            # Store the path for lazy loading
            renderer_ref = lambda: self._lazy_load_renderer(module_path, function_name)
        elif renderer:
            renderer_ref = renderer
        else:
            raise ValueError(f"Must provide either renderer or module_path+function_name")
        
        template = TemplateInfo(
            id=template_id,
            name=name,
            description=description,
            renderer=renderer_ref if renderer else renderer_ref,
            module_path=module_path or (inspect.getmodule(renderer).__name__ if renderer else ""),
            required_fields=required_fields or [],
            category=category,
            format=format,
            version=version,
            tags=tags or []
        )
        
        self._templates[template_id] = template
        
        # Update category index
        if category not in self._categories:
            self._categories[category] = []
        if template_id not in self._categories[category]:
            self._categories[category].append(template_id)
        
        logger.info(f"Registered template: {template_id} ({category})")
    
    def _lazy_load_renderer(self, module_path: str, function_name: str) -> Callable:
        """Lazy load a renderer function from a module"""
        cache_key = f"{module_path}:{function_name}"
        
        if cache_key not in self._renderer_cache:
            try:
                module = importlib.import_module(module_path)
                renderer = getattr(module, function_name)
                self._renderer_cache[cache_key] = renderer
                logger.debug(f"Loaded renderer {function_name} from {module_path}")
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load renderer {function_name} from {module_path}: {e}")
                raise
        
        return self._renderer_cache[cache_key]
    
    def render(
        self,
        template_id: str,
        payload: Any,
        kb: Optional[Any] = None,
        **kwargs
    ) -> str:
        """
        Render a template with the given payload.
        
        Args:
            template_id: Template to render
            payload: Data payload (dict or Pydantic model)
            kb: Optional knowledge base
            **kwargs: Additional arguments for the renderer
            
        Returns:
            Rendered output as string
        """
        if template_id not in self._templates:
            raise ValueError(f"Template {template_id} not found. Available: {list(self._templates.keys())}")
        
        template = self._templates[template_id]
        
        # Validate required fields if payload is a dict
        if isinstance(payload, dict):
            missing = [f for f in template.required_fields if f not in payload]
            if missing:
                logger.warning(f"Template {template_id} missing fields: {missing}")
        
        # Get the renderer (may trigger lazy loading)
        renderer = template.renderer
        if callable(renderer):
            # If renderer is a lambda (lazy loader), call it
            if renderer.__name__ == '<lambda>':
                renderer = renderer()
        
        # Call the renderer
        try:
            if kb is not None:
                return renderer(payload, kb, **kwargs)
            else:
                # Try with just payload first
                sig = inspect.signature(renderer)
                if len(sig.parameters) == 1:
                    return renderer(payload, **kwargs)
                else:
                    return renderer(payload, None, **kwargs)
        except Exception as e:
            logger.error(f"Failed to render template {template_id}: {e}")
            raise
    
    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get template metadata"""
        return self._templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None, tags: Optional[List[str]] = None) -> List[TemplateInfo]:
        """
        List available templates, optionally filtered.
        
        Args:
            category: Filter by category
            tags: Filter by tags (any match)
            
        Returns:
            List of template info objects
        """
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        return templates
    
    def get_categories(self) -> Dict[str, List[str]]:
        """Get all categories and their templates"""
        return self._categories.copy()
    
    def validate_payload(self, template_id: str, payload: Any) -> Tuple[bool, List[str]]:
        """
        Validate that a payload has required fields for a template.
        
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        if template_id not in self._templates:
            return False, [f"Template {template_id} not found"]
        
        template = self._templates[template_id]
        
        if isinstance(payload, dict):
            missing = [f for f in template.required_fields if f not in payload]
        else:
            # For Pydantic models, check attributes
            missing = [f for f in template.required_fields if not hasattr(payload, f)]
        
        return len(missing) == 0, missing
    
    def get_renderer_directly(self, template_id: str) -> Optional[Callable]:
        """Get the raw renderer function for a template"""
        if template_id not in self._templates:
            return None
        
        template = self._templates[template_id]
        renderer = template.renderer
        
        # Resolve lazy loading if needed
        if callable(renderer) and renderer.__name__ == '<lambda>':
            renderer = renderer()
        
        return renderer


def bootstrap_registry(registry: TemplateRegistry) -> None:
    """
    Bootstrap the registry with all known templates.
    
    This function registers all available templates from:
    - ProposalOS RGE system
    - Cost Volume Assembly modules
    - DFARS/FAR templates
    - Custom report generators
    """
    
    # ============================================================
    # DFARS Templates
    # ============================================================
    
    registry.register(
        template_id="DFARS_CHECKLIST",
        name="DFARS 252.215-7009 Requirements Checklist",
        description="Compliance checklist for certified cost or pricing data",
        module_path="proposalos_rge.render.md.dfars_templates",
        function_name="render_dfars_checklist",
        required_fields=["facts"],
        category="DFARS",
        tags=["compliance", "checklist", "252.215-7009"]
    )
    
    registry.register(
        template_id="DFARS_COVER_PAGE",
        name="DFARS Cover Page (SF1411-style)",
        description="Contract pricing proposal cover sheet",
        module_path="proposalos_rge.render.md.dfars_templates",
        function_name="render_dfars_cover_page",
        required_fields=["allocations"],
        category="DFARS",
        tags=["cover", "SF1411", "pricing"]
    )
    
    # ============================================================
    # Annual/Fiscal Reports
    # ============================================================
    
    registry.register(
        template_id="ANNUAL_FY",
        name="Annual Fiscal Year Rollup",
        description="Per-FY cost rollups at selected level",
        module_path="proposalos_rge.render.md.annual_fy",
        function_name="render",
        required_fields=["allocations"],
        category="Financial",
        tags=["fiscal", "annual", "rollup"]
    )
    
    # ============================================================
    # Cost Volume Assembly Templates
    # ============================================================
    
    # Check if alternative DFARS templates exist
    try:
        registry.register(
            template_id="DFARS_CHECKLIST_ALT",
            name="DFARS Checklist (Alternative)",
            description="Alternative DFARS compliance checklist implementation",
            module_path="Cost_Volume_Assembly.Costing,Pricing Reports.render_md_dfars_templates",
            function_name="render_dfars_checklist",
            required_fields=["facts"],
            category="DFARS",
            tags=["compliance", "checklist", "alternative"]
        )
    except:
        logger.debug("Alternative DFARS checklist not available")
    
    try:
        registry.register(
            template_id="DFARS_COVER_PAGE_ALT",
            name="DFARS Cover Page (Alternative)",
            description="Alternative DFARS cover page implementation",
            module_path="Cost_Volume_Assembly.Costing,Pricing Reports.render_md_dfars_templates",
            function_name="render_dfars_cover_page",
            required_fields=["allocations"],
            category="DFARS",
            tags=["cover", "alternative"]
        )
    except:
        logger.debug("Alternative DFARS cover page not available")
    
    # ============================================================
    # FAR Templates
    # ============================================================
    
    registry.register(
        template_id="FAR_15_408_TABLE_15_2",
        name="FAR 15.408 Table 15-2",
        description="Cost element summary per FAR requirements",
        module_path="proposalos_rge.render.md.far_templates",
        function_name="render_far_table_15_2",
        required_fields=["allocations"],
        category="FAR",
        tags=["FAR", "15.408", "table", "cost-elements"],
        version="1.0.0"
    )
    
    # ============================================================
    # Cost Volume Templates
    # ============================================================
    
    registry.register(
        template_id="COST_VOLUME_EXECUTIVE",
        name="Cost Volume Executive Summary",
        description="Executive summary for cost volume",
        module_path="proposalos_rge.render.md.cost_volume",
        function_name="render_executive_summary",
        required_fields=["facts", "allocations"],
        category="Cost Volume",
        tags=["executive", "summary", "cost"]
    )
    
    registry.register(
        template_id="COST_VOLUME_BUILDUP",
        name="Cost Buildup Details",
        description="Detailed cost buildup by element",
        module_path="proposalos_rge.render.md.cost_volume",
        function_name="render_cost_buildup",
        required_fields=["allocations"],
        category="Cost Volume",
        tags=["buildup", "details", "cost"]
    )
    
    registry.register(
        template_id="COST_VOLUME_COMPLIANCE",
        name="Regulatory Compliance Section",
        description="Regulatory compliance documentation",
        module_path="proposalos_rge.render.md.cost_volume",
        function_name="render_compliance",
        required_fields=["facts"],
        category="Cost Volume",
        tags=["compliance", "regulatory"]
    )
    
    # ============================================================
    # Travel Templates
    # ============================================================
    
    registry.register(
        template_id="TRAVEL_SUMMARY",
        name="Travel Cost Summary",
        description="Travel cost calculations with GSA rates",
        module_path="proposalos_rge.render.md.travel",
        function_name="render_summary",
        required_fields=["allocations"],
        category="Travel",
        tags=["travel", "GSA", "per-diem"]
    )
    
    # ============================================================
    # Composite Templates (Multiple Sections)
    # ============================================================
    
    registry.register(
        template_id="COST_VOLUME_FULL",
        name="Complete Cost Volume",
        description="Full cost volume with all sections",
        module_path="proposalos_rge.render.composite",
        function_name="render_full_cost_volume",
        required_fields=["facts", "allocations", "assumptions"],
        category="Composite",
        tags=["complete", "cost-volume", "all-sections"]
    )
    
    registry.register(
        template_id="PROPOSAL_PACKAGE",
        name="Complete Proposal Package",
        description="All proposal documents in one render",
        module_path="proposalos_rge.render.composite",
        function_name="render_proposal_package",
        required_fields=["facts", "allocations", "assumptions", "hefs"],
        category="Composite",
        tags=["complete", "package", "all-documents"]
    )
    
    # ============================================================
    # Custom/Special Templates
    # ============================================================
    
    registry.register(
        template_id="BOE_NARRATIVE",
        name="Basis of Estimate Narrative",
        description="Narrative explanation of cost estimates",
        module_path="proposalos_rge.render.md.boe",
        function_name="render_boe_narrative",
        required_fields=["facts", "assumptions"],
        category="BOE",
        tags=["narrative", "basis", "estimate"]
    )
    
    registry.register(
        template_id="RISK_ASSESSMENT",
        name="Cost Risk Assessment",
        description="Risk assessment and mitigation strategies",
        module_path="proposalos_rge.render.md.risk",
        function_name="render_risk_assessment",
        required_fields=["facts", "allocations"],
        category="Risk",
        tags=["risk", "assessment", "mitigation"]
    )
    
    # ============================================================
    # Debug/Test Templates
    # ============================================================
    
    registry.register(
        template_id="DEBUG_DUMP",
        name="Debug Payload Dump",
        description="Raw JSON dump of payload for debugging",
        module_path="proposalos_rge.render.debug",
        function_name="render_debug_dump",
        required_fields=[],
        category="Debug",
        tags=["debug", "test", "dump"]
    )
    
    logger.info(f"Registry bootstrapped with {len(registry._templates)} templates")
    logger.info(f"Categories: {list(registry.get_categories().keys())}")


def create_default_registry() -> TemplateRegistry:
    """
    Create and bootstrap a default registry.
    
    Returns:
        Fully configured TemplateRegistry
    """
    registry = TemplateRegistry()
    bootstrap_registry(registry)
    return registry


# ============================================================
# Convenience Functions
# ============================================================

def list_available_templates(registry: Optional[TemplateRegistry] = None) -> None:
    """Print a formatted list of all available templates"""
    if registry is None:
        registry = create_default_registry()
    
    print("\n" + "="*60)
    print("Available Report Templates")
    print("="*60)
    
    categories = registry.get_categories()
    
    for category, template_ids in sorted(categories.items()):
        print(f"\n{category}:")
        print("-" * len(category))
        
        for tid in template_ids:
            template = registry.get_template(tid)
            if template:
                print(f"  • {tid}: {template.name}")
                print(f"    {template.description}")
                if template.required_fields:
                    print(f"    Required: {', '.join(template.required_fields)}")
    
    print("\n" + "="*60)
    print(f"Total: {len(registry._templates)} templates available")
    print("="*60)


def validate_all_templates(registry: Optional[TemplateRegistry] = None) -> Dict[str, bool]:
    """
    Validate that all registered templates can be loaded.
    
    Returns:
        Dict mapping template_id to success status
    """
    if registry is None:
        registry = create_default_registry()
    
    results = {}
    
    for template_id in registry._templates:
        try:
            renderer = registry.get_renderer_directly(template_id)
            results[template_id] = renderer is not None
        except Exception as e:
            logger.error(f"Failed to load {template_id}: {e}")
            results[template_id] = False
    
    return results


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create and bootstrap registry
    registry = create_default_registry()
    
    # List all templates
    list_available_templates(registry)
    
    # Validate all templates can load
    print("\nValidating template loading...")
    results = validate_all_templates(registry)
    
    failed = [tid for tid, success in results.items() if not success]
    if failed:
        print(f"⚠️  Failed to load: {failed}")
    else:
        print("✅ All templates validated successfully")
    
    # Example: Render a template
    print("\nExample rendering:")
    
    # Create sample payload
    sample_payload = {
        "ui": {"contract_type": "CPFF", "fiscal_years": ["FY2025"]},
        "facts": [
            {
                "element": "Direct Labor",
                "classification": "direct",
                "confidence": 0.9
            }
        ],
        "allocations": [
            {
                "fy": "FY2025",
                "task": "Direct Labor",
                "cost": 100000
            }
        ]
    }
    
    # Try to render DFARS checklist
    try:
        output = registry.render("DFARS_CHECKLIST", sample_payload)
        print("DFARS Checklist rendered successfully!")
        print(f"Output length: {len(output)} characters")
    except Exception as e:
        print(f"Failed to render: {e}")
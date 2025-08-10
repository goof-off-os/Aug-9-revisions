# registry_bootstrap.py
"""
Bootstrap the ProposalOS template registry in one place.
- Discovers and registers Markdown renderers (e.g., DFARS, Annual FY).
- Exposes a simple TemplateRegistry wrapper for safer access.
- Intended to be imported by FastAPI startup (e.g., in main.py).

Usage:
    from registry_bootstrap import TemplateRegistry, bootstrap_registry

    TEMPLATE_REGISTRY = TemplateRegistry()
    bootstrap_registry(TEMPLATE_REGISTRY)

    # Later, in handlers:
    md = TEMPLATE_REGISTRY.render("DFARS_COVER_PAGE", payload, kb)
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional

logger = logging.getLogger(__name__)

Renderer = Callable[[dict | Any, dict | None], str]

@dataclass
class TemplateEntry:
    title: str
    renderer: Renderer
    category: str = "GENERAL"
    content_type: str = "text/markdown"

@dataclass
class TemplateRegistry:
    _store: Dict[str, TemplateEntry] = field(default_factory=dict)

    def register(self, key: str, *, title: str, renderer: Renderer, category: str = "GENERAL", content_type: str = "text/markdown") -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("Template key must be a non-empty string.")
        self._store[key] = TemplateEntry(title=title, renderer=renderer, category=category, content_type=content_type)

    def has(self, key: str) -> bool:
        return key in self._store

    def keys(self) -> Iterable[str]:
        return self._store.keys()

    def info(self, key: str) -> dict:
        e = self._store[key]
        return {"title": e.title, "category": e.category, "content_type": e.content_type}

    def render(self, key: str, payload: dict | Any, kb: Optional[dict] = None) -> str:
        if key not in self._store:
            raise KeyError(f"Unknown template key: {key}")
        return self._store[key].renderer(payload, kb)

def _safe_register_module(mod, registry: TemplateRegistry) -> int:
    """Call module.register(registry) if present; return number of keys before/after to detect additions."""
    before = set(registry.keys())
    register = getattr(mod, "register", None)
    if callable(register):
        try:
            register(registry)  # type: ignore[arg-type]
            after = set(registry.keys())
            return len(after - before)
        except Exception as e:
            logger.exception("Failed to register templates from %s: %s", mod.__name__, e)
    return 0

def _discover_and_register(registry: TemplateRegistry, package: str) -> int:
    """Import all modules in a package (e.g., 'render.md') and call register() if present."""
    added = 0
    try:
        pkg = importlib.import_module(package)
    except Exception as e:
        logger.warning("Package '%s' not importable yet: %s", package, e)
        return 0

    if not hasattr(pkg, "__path__"):
        # Single module case
        return _safe_register_module(pkg, registry)

    for m in pkgutil.iter_modules(pkg.__path__, package + "."):
        try:
            mod = importlib.import_module(m.name)
            added += _safe_register_module(mod, registry)
        except Exception as e:
            logger.exception("Error importing %s: %s", m.name, e)
    return added

def bootstrap_registry(registry: TemplateRegistry) -> TemplateRegistry:
    """
    Central place to plug new template families:
      - render.md.dfars_templates          (DFARS)
      - render.md.annual_fy_templates      (Annual Fiscal Year)
      - render.md.*                        (any other families)
    """
    total = 0
    # Explicit known modules first (safe if missing)
    for mod_name in [
        "render.md.dfars_templates",
        "render.md.annual_fy_templates",
    ]:
        try:
            mod = importlib.import_module(mod_name)
            total += _safe_register_module(mod, registry)
        except Exception as e:
            logger.info("Optional template module '%s' not loaded: %s", mod_name, e)

    # Then sweep the whole render.md package for any new stuff
    total += _discover_and_register(registry, "render.md")
    logger.info("Template registry bootstrap complete. Added %d templates.", total)
    return registry

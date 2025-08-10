
#!/usr/bin/env python3
"""
project_audit.py — Single-file codebase auditor & blueprint generator

What it does
------------
- Scans a Python project (default: current directory) and generates a Markdown report.
- Sections: Project status, technical blueprint, ontology snapshot (from KB JSON if present),
  functionality inventory (APIs, renderers, templates), and quality review across correctness,
  security, performance, and maintainability.
- Identifies potential bugs, bottlenecks, and code smells; suggests best-practice fixes and tests.

Usage
-----
    python project_audit.py --root /path/to/repo --kb KB_cleaned.json --out report.md

All args optional; sensible defaults inferred.
"""

from __future__ import annotations
import argparse
import ast
import io
import json
import os
import re
import sys
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# ------------------------ helpers ------------------------

PY_EXT = {".py"}

def iter_py_files(root: Path) -> List[Path]:
    files = []
    for p in root.rglob("*.py"):
        # ignore common virtualenv/build dirs
        if any(seg in {".venv", "venv", "__pycache__", "build", "dist"} for seg in p.parts):
            continue
        files.append(p)
    return sorted(files)

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return path.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""

def short(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)

# ------------------------ AST metrics ------------------------

@dataclass
class FunctionInfo:
    name: str
    lineno: int
    endlineno: int
    args: int
    is_async: bool
    complexity: int
    decorators: List[str] = field(default_factory=list)

@dataclass
class ModuleInfo:
    path: Path
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    endpoints: List[Tuple[str, str, int]] = field(default_factory=list)  # (method, route, lineno)
    issues: List[str] = field(default_factory=list)

ASYNC_HTTP_NAMES = {"requests"}  # naive: requests in async funcs
DANGEROUS_CALLS = {
    "eval": "Use of eval() can execute arbitrary code.",
    "exec": "Use of exec() can execute arbitrary code.",
    "pickle.load": "pickle.load is unsafe with untrusted data. Prefer json or a safe format.",
    "pickle.loads": "pickle.loads is unsafe with untrusted data.",
    "yaml.load": "yaml.load without SafeLoader is unsafe; use safe_load.",
}
SHELLY = {"os.system", "subprocess.Popen", "subprocess.run", "subprocess.call"}

def cyclomatic_complexity(node: ast.AST) -> int:
    """Very small CC approximation: increments on branching nodes."""
    increments = (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler, ast.With, ast.Try, ast.BoolOp, ast.IfExp, ast.Match)
    count = 1
    for n in ast.walk(node):
        if isinstance(n, increments):
            count += 1
    return count

def decorator_names(node: ast.AST) -> List[str]:
    out = []
    if hasattr(node, "decorator_list"):
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                out.append(d.id)
            elif isinstance(d, ast.Attribute):
                out.append(d.attr)
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name):
                    out.append(d.func.id)
                elif isinstance(d.func, ast.Attribute):
                    out.append(d.func.attr)
    return out

def is_fastapi_decorator(name: str) -> bool:
    return name in {"get", "post", "put", "delete", "patch", "options"} or name.endswith("router")

def find_endpoints(tree: ast.AST) -> List[Tuple[str, str, int]]:
    """Heuristically find FastAPI endpoints: @app.get('/x') etc."""
    eps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for d in node.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
                    method = d.func.attr.upper()
                    if method in {"GET","POST","PUT","DELETE","PATCH","OPTIONS"}:
                        route = None
                        if d.args and isinstance(d.args[0], ast.Constant) and isinstance(d.args[0].value, str):
                            route = d.args[0].value
                        elif any(kw.arg=="path" for kw in d.keywords):
                            for kw in d.keywords:
                                if kw.arg=="path" and isinstance(kw.value, ast.Constant):
                                    route = kw.value.value
                        eps.append((method, route or "<dynamic>", getattr(node, "lineno", 0)))
    return eps

def detect_issues(tree: ast.AST, source: str) -> List[str]:
    issues = []
    # Bare except, broad except
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append(f"Correctness: bare 'except' at L{node.lineno}. Catch specific exceptions.")
            elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
                issues.append(f"Correctness: broad exception '{node.type.id}' at L{node.lineno}. Narrow the scope.")
            # no-op except
            if len(node.body)==1 and isinstance(node.body[0], ast.Pass):
                issues.append(f"Code smell: empty except block (pass) at L{node.lineno}. Consider logging & handling.")
    # Mutable default args
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append(f"Correctness: mutable default argument in '{node.name}' at L{node.lineno}. Use None and set inside.")
    # prints instead of logging
    if re.search(r"(?m)^\s*print\(", source):
        issues.append("Maintainability: direct print() detected. Prefer structured logging.")
    # TODO/FIXME density
    todos = len(re.findall(r"(?i)#\s*(todo|fixme)", source))
    if todos:
        issues.append(f"Maintainability: {todos} TODO/FIXME notes present.")
    # Security: dangerous calls
    for name, msg in DANGEROUS_CALLS.items():
        pat = r"\b" + re.escape(name) + r"\b"
        if re.search(pat, source):
            issues.append(f"Security: {msg}")
    # shell calls
    shell_hits = re.findall(r"\b(subprocess\.(run|Popen|call)|os\.system)\s*\(", source)
    if shell_hits:
        issues.append("Security: shell execution detected. Avoid shell=True; sanitize inputs.")
    # yaml.load without SafeLoader
    if re.search(r"\byaml\.load\s*\(", source) and "SafeLoader" not in source:
        issues.append("Security: yaml.load without SafeLoader; use yaml.safe_load or specify SafeLoader.")
    # potential secret patterns
    secret_patterns = [
        (r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "Possible hardcoded API key."),
        (r"(?i)secret\s*=\s*['\"][A-Za-z0-9_\-]{12,}['\"]", "Possible hardcoded secret."),
    ]
    for pat, note in secret_patterns:
        if re.search(pat, source):
            issues.append(f"Security: {note}")
    return issues

def scan_module(path: Path, root: Path) -> ModuleInfo:
    src = read_text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(src)
    except Exception as e:
        return ModuleInfo(path=path, issues=[f"Parse error: {e}"])

    mi = ModuleInfo(path=path)
    mi.endpoints.extend(find_endpoints(tree))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            endlineno = getattr(node, "end_lineno", node.lineno)
            fi = FunctionInfo(
                name=node.name,
                lineno=node.lineno,
                endlineno=endlineno,
                args=len(getattr(node.args, "args", [])),
                is_async=isinstance(node, ast.AsyncFunctionDef),
                complexity=cyclomatic_complexity(node),
                decorators=decorator_names(node),
            )
            mi.functions.append(fi)
        elif isinstance(node, ast.ClassDef):
            mi.classes.append(node.name)

    mi.issues.extend(detect_issues(tree, src))
    return mi

# --------------------- Ontology snapshot ---------------------

def summarize_kb(kb_path: Optional[Path]) -> Tuple[str, Dict[str, int]]:
    if not kb_path or not kb_path.exists():
        return "_KB not found — skipping ontology snapshot._", {}
    try:
        data = json.loads(kb_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return f"_Failed to load KB: {e}_", {}
    # Expect either {'facts': [...]} or a list/dict of elements
    elements = []
    if isinstance(data, dict):
        if "facts" in data and isinstance(data["facts"], list):
            for f in data["facts"]:
                el = (f.get("element") or f.get("type") or "Unknown").strip()
                if el:
                    elements.append(el)
        else:
            elements.extend(data.keys())
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                el = item.get("element") or item.get("type")
                if el:
                    elements.append(el)
    counts = Counter(elements)
    lines = ["**Ontology elements (top 15):**"]
    for k, v in counts.most_common(15):
        lines.append(f"- {k}: {v}")
    if not counts:
        lines = ["_KB loaded, but no recognizable 'facts' elements to summarize._"]
    return "\n".join(lines), counts

# --------------------- Reporting ---------------------

def md_table(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    widths = [max(len(str(cell)) for cell in col) for col in zip(*rows)]
    def fmt(row):
        return "| " + " | ".join(str(c).ljust(w) for c, w in zip(row, widths)) + " |"
    header = fmt(rows[0])
    sep = "| " + " | ".join("-"*w for w in widths) + " |"
    body = "\n".join(fmt(r) for r in rows[1:])
    return "\n".join([header, sep, body])

def suggest_for_function(fi: FunctionInfo) -> List[str]:
    s = []
    if fi.complexity >= 10:
        s.append(f"High cyclomatic complexity ({fi.complexity}). Consider refactor into helpers.")
    if (fi.endlineno - fi.lineno) > 80:
        s.append(f"Long function ({fi.endlineno - fi.lineno} LOC). Extract smaller functions.")
    if fi.args > 6:
        s.append(f"Many parameters ({fi.args}). Consider grouping with dataclass/pydantic model.")
    return s

def aggregate_findings(mods: List[ModuleInfo]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    out["total_files"] = len(mods)
    out["total_functions"] = sum(len(m.functions) for m in mods)
    out["avg_complexity"] = round(sum(f.complexity for m in mods for f in m.functions) / max(1, out["total_functions"]), 2)
    out["long_functions"] = [(short(m.path, ROOT), f.name, f.endlineno - f.lineno) 
                             for m in mods for f in m.functions if (f.endlineno - f.lineno) > 80]
    out["complex_functions"] = [(short(m.path, ROOT), f.name, f.complexity) 
                                for m in mods for f in m.functions if f.complexity >= 10]
    out["endpoints"] = [(short(m.path, ROOT), *ep) for m in mods for ep in m.endpoints]
    out["issues"] = [(short(m.path, ROOT), iss) for m in mods for iss in m.issues]
    return out

# --------------------- Main ---------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--kb", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="Write Markdown report to this file")
    args = parser.parse_args()

    root = args.root.resolve()
    global ROOT
    ROOT = root

    py_files = iter_py_files(root)
    mods: List[ModuleInfo] = []
    for p in py_files:
        mods.append(scan_module(p, root))

    summary = aggregate_findings(mods)

    kb_section, _counts = summarize_kb(args.kb)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

    # ---------- Build Markdown ----------
    lines: List[str] = []
    lines.append(f"# Project Status & Technical Blueprint\n")
    lines.append(f"_Generated: {now}_\n")
    lines.append(f"**Scanned root:** `{root}`  \n**Python files:** {summary['total_files']}  \n**Total functions:** {summary['total_functions']}  \n**Avg cyclomatic complexity:** {summary['avg_complexity']}\n")

    # Blueprint / Components
    lines.append("## Technical Blueprint\n- **Core modules discovered:**")
    for p in py_files:
        lines.append(f"  - `{short(p, root)}`")
    lines.append("\n- **HTTP endpoints (FastAPI heuristics):**")
    if summary["endpoints"]:
        rows = [["File", "Method", "Route", "Line"]]
        for f, method, route, ln in summary["endpoints"]:
            rows.append([f, method, route, str(ln)])
        lines.append(md_table(rows))
    else:
        lines.append("_No FastAPI endpoints found via decorators — if present, ensure they use @app.<method> decoractors._")

    # Ontology
    lines.append("\n## Ontology Snapshot\n")
    lines.append(kb_section + "\n")

    # Functionality inventory: template/renderer discovery
    lines.append("## Functionality Inventory (Renderers & Templates)\n")
    renderers = []
    for m in mods:
        for f in m.functions:
            if f.name.startswith("render_"):
                renderers.append((short(m.path, root), f.name, f.lineno))
    if renderers:
        rows = [["File", "Renderer", "Line"]]
        for r in renderers:
            rows.append([r[0], r[1], str(r[2])])
        lines.append(md_table(rows))
    else:
        lines.append("_No render_* functions found. If using a registry, ensure renderers follow a discoverable naming convention._")

    # Quality sections
    lines.append("\n## Quality Review\n### Correctness\n")
    corr = [i for i in summary["issues"] if i[1].startswith("Correctness")]
    if corr:
        rows = [["File", "Issue"]]
        rows += [[f, iss] for f, iss in corr]
        lines.append(md_table(rows))
    else:
        lines.append("_No obvious correctness issues detected._")

    lines.append("\n### Security\n")
    sec = [i for i in summary["issues"] if i[1].startswith("Security")]
    if sec:
        rows = [["File", "Issue"]]
        rows += [[f, iss] for f, iss in sec]
        lines.append(md_table(rows))
    else:
        lines.append("_No obvious security smells detected._")

    lines.append("\n### Performance\n")
    perf_rows = [["File", "Function", "Concern"]]
    perf_hits = 0
    for m in mods:
        for f in m.functions:
            if f.complexity >= 12:
                perf_rows.append([short(m.path, root), f.name, f"High complexity ({f.complexity}) may affect performance."])
                perf_hits += 1
            if (f.endlineno - f.lineno) > 150:
                perf_rows.append([short(m.path, root), f.name, f"Very long function ({f.endlineno - f.lineno} LOC) may be slow."])
                perf_hits += 1
    if perf_hits:
        lines.append(md_table(perf_rows))
    else:
        lines.append("_No obvious performance bottlenecks detected via static analysis._")

    lines.append("\n### Maintainability & Code Smells\n")
    maint_rows = [["File", "Function/Context", "Smell / Suggestion"]]
    smell_hits = 0
    for m in mods:
        for f in m.functions:
            for s in suggest_for_function(f):
                maint_rows.append([short(m.path, root), f.name, s])
                smell_hits += 1
        # generic file-level issues
        for iss in m.issues:
            if iss.startswith("Maintainability") or iss.startswith("Code smell"):
                maint_rows.append([short(m.path, root), "-", iss])
                smell_hits += 1
    if smell_hits:
        lines.append(md_table(maint_rows))
    else:
        lines.append("_No major maintainability concerns detected._")

    # Suggestions section
    lines.append("\n## Recommendations & Best Practices\n")
    lines.append("- Enforce type checking (mypy/pyright) and docstrings for all public functions.\n"
                 "- Replace bare/broad exceptions with specific ones; log with structured context.\n"
                 "- Avoid `print`; use `logging.getLogger(__name__)` with consistent formatting.\n"
                 "- Add input validation via Pydantic models at all boundaries (API & internal services).\n"
                 "- Extract functions with CC >= 10 or >80 LOC; prefer pure functions for testability.\n"
                 "- Replace unsafe calls (eval/exec/pickle/yaml.load) with safer alternatives.\n"
                 "- Prefer dependency injection for I/O (files, network) to enable fast unit tests.\n"
                 "- Add rate limiting, authZ default‑deny, and request size/time limits on FastAPI endpoints.\n"
                 "- Cache expensive pure computations (functools.lru_cache) when appropriate.\n"
                 "- Ship a pre-commit config (ruff/black/isort, mypy) and a CI run (pytest -q).\n")

    # Test coverage plan
    lines.append("\n## Targeted Test Coverage Plan\n")
    lines.append("1. **Schema tests**: Validate Pydantic models with representative payloads (happy/edge).\n"
                 "2. **Renderer tests**: Golden-file markdown comparisons for each `render_*` function.\n"
                 "3. **Validator tests**: Given contrived bad inputs, assert specific flags/errors.\n"
                 "4. **API tests**: FastAPI TestClient for /reports/* with auth, size, and timeouts.\n"
                 "5. **Regression tests**: Lock fixtures for KB parsing and template registry wiring.\n"
                 "6. **Property tests**: Fuzz table builders (no crashes, idempotent, valid Markdown).\n")

    # File-specific detail appendix
    lines.append("\n## Appendix: File Details\n")
    for m in mods:
        lines.append(f"### {short(m.path, root)}")
        if m.functions:
            rows = [["Function", "Line", "LOC", "Async", "Args", "CC"]]
            for f in m.functions:
                rows.append([f.name, str(f.lineno), str(f.endlineno - f.lineno), "yes" if f.is_async else "no", str(f.args), str(f.complexity)])
            lines.append(md_table(rows))
        if m.classes:
            lines.append("- **Classes:** " + ", ".join(m.classes))
        if m.endpoints:
            rows = [["Method", "Route", "Line"]]
            for method, route, ln in m.endpoints:
                rows.append([method, route, str(ln)])
            lines.append(md_table(rows))
        if m.issues:
            rows = [["Issue"]]
            rows += [[iss] for iss in m.issues]
            lines.append(md_table(rows))
        lines.append("")

    report = "\n".join(lines).strip() + "\n"

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Wrote report → {args.out}")
    else:
        print(report)

if __name__ == "__main__":
    main()

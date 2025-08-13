# proposalos_rge/api/endpoints.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from importlib import import_module
from typing import Optional, Dict, Any, List
import io
import json

from ..schemas import UnifiedPayload, UIInputs
from ..registry import REGISTRY, get_template
from ..inputs.kb_loader import load_kb_to_payload, load_rfp_extraction_to_payload
from ..normalize.builder import build_unified_payload
from ..validate.rules import run_validators

router = APIRouter(prefix="/reports", tags=["reports"])


class PreviewBody(BaseModel):
    ui: UIInputs
    kb_path: Optional[str] = None
    payload: Optional[UnifiedPayload] = None
    template: str = "ANNUAL_FY"
    extraction_response: Optional[Dict[str, Any]] = None
    additional_data: Optional[Dict[str, Any]] = None


class GenerateBody(PreviewBody):
    export_format: Optional[str] = "markdown"  # markdown, json, csv
    export_options: Optional[Dict[str, Any]] = {}


class TemplateListResponse(BaseModel):
    templates: Dict[str, Dict[str, Any]]


class ValidationResponse(BaseModel):
    is_valid: bool
    warnings: List[Dict[str, str]]
    errors: List[Dict[str, str]]
    payload: Dict[str, Any]


@router.get("/templates", response_model=TemplateListResponse)
def list_templates():
    """
    List all available report templates
    
    Returns:
        Dictionary of template specifications
    """
    return {"templates": REGISTRY}


@router.get("/templates/{template_id}")
def get_template_info(template_id: str):
    """
    Get detailed information about a specific template
    
    Args:
        template_id: Template identifier
        
    Returns:
        Template specification
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(404, f"Template '{template_id}' not found")
    return template


@router.post("/validate", response_model=ValidationResponse)
def validate_only(body: PreviewBody):
    """
    Validate payload without generating report
    
    Args:
        body: Preview request body
        
    Returns:
        Validation results
    """
    # Build payload from various sources
    if body.payload:
        payload = body.payload
    elif body.kb_path:
        payload = load_kb_to_payload(body.kb_path, body.ui)
    elif body.extraction_response:
        payload = load_rfp_extraction_to_payload(body.extraction_response, body.ui)
    else:
        raise HTTPException(400, "Provide either payload, kb_path, or extraction_response")
    
    # Build and validate
    payload = build_unified_payload(body.ui, payload, body.additional_data)
    payload = run_validators(payload)
    
    # Extract validation results
    warnings = [
        {"code": e.code, "message": e.message}
        for e in payload.audit.validations
        if e.kind == "warning"
    ]
    errors = [
        {"code": e.code, "message": e.message}
        for e in payload.audit.validations
        if e.kind == "error"
    ]
    
    return ValidationResponse(
        is_valid=len(errors) == 0,
        warnings=warnings,
        errors=errors,
        payload=payload.dict()
    )


@router.post("/preview")
def preview(body: PreviewBody):
    """
    Generate report preview
    
    Args:
        body: Preview request body
        
    Returns:
        Rendered report sections and audit results
    """
    # Validate template exists
    if body.template not in REGISTRY:
        raise HTTPException(404, f"Unknown template '{body.template}'")
    
    # Build payload from various sources
    if body.payload:
        payload = body.payload
    elif body.kb_path:
        payload = load_kb_to_payload(body.kb_path, body.ui)
    elif body.extraction_response:
        payload = load_rfp_extraction_to_payload(body.extraction_response, body.ui)
    else:
        # Create empty payload if nothing provided
        payload = UnifiedPayload(ui=body.ui)
    
    # Build, normalize, and validate
    payload = build_unified_payload(body.ui, payload, body.additional_data)
    payload = run_validators(payload)
    
    # Render sections
    rendered_sections = []
    template_spec = REGISTRY[body.template]
    
    for section in template_spec.get("sections", []):
        try:
            # Import and call renderer
            renderer_path = section["renderer"]
            if ":" in renderer_path:
                mod_path, fn_name = renderer_path.split(":")
            else:
                mod_path = renderer_path
                fn_name = "render"
            
            module = import_module(mod_path)
            render_fn = getattr(module, fn_name)
            
            # Render section
            rendered_content = render_fn(payload)
            
            rendered_sections.append({
                "id": section["id"],
                "title": section.get("title", ""),
                "content": rendered_content
            })
            
        except Exception as e:
            rendered_sections.append({
                "id": section["id"],
                "title": section.get("title", ""),
                "content": f"Error rendering section: {str(e)}"
            })
    
    return {
        "template": body.template,
        "audit": payload.audit.dict(),
        "sections": rendered_sections,
        "metadata": {
            "generated_at": payload.generated_at_utc,
            "total_facts": len(payload.facts),
            "total_allocations": len(payload.allocations)
        }
    }


@router.post("/generate")
def generate(body: GenerateBody):
    """
    Generate final report with export options
    
    Args:
        body: Generate request body
        
    Returns:
        Generated report in requested format
    """
    # First generate the preview
    preview_result = preview(body)
    
    # Handle different export formats
    if body.export_format == "json":
        # Return raw JSON
        return preview_result
    
    elif body.export_format == "csv":
        # Export allocations as CSV
        if body.payload and body.payload.allocations:
            output = io.StringIO()
            
            # Write CSV header
            output.write("FY,CLIN,WBS,Task,IPT,Hours,Rate,Cost\n")
            
            # Write allocation rows
            for alloc in body.payload.allocations:
                output.write(
                    f"{alloc.fy},{alloc.clin or ''},{alloc.wbs or ''},{alloc.task or ''},{alloc.ipt or ''},{alloc.hours},{alloc.rate or ''},{alloc.cost or ''}\n"
                )
            
            # Return as streaming response
            output.seek(0)
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{body.template}.csv"
                }
            )
        else:
            raise HTTPException(400, "No allocations to export as CSV")
    
    else:  # Default to markdown
        # Combine all sections into single markdown document
        lines = []
        
        # Add metadata header
        lines.extend([
            f"# {REGISTRY[body.template]['name']}",
            f"",
            f"*{REGISTRY[body.template]['description']}*",
            f"",
            f"---",
            f""
        ])
        
        # Add each section
        for section in preview_result["sections"]:
            if section.get("title"):
                lines.append(f"## {section['title']}")
                lines.append("")
            lines.append(section["content"])
            lines.append("")
        
        # Add audit summary at end
        if preview_result["audit"]["validations"] or preview_result["audit"]["conflicts"]:
            lines.extend([
                "---",
                "",
                "## Report Validation",
                ""
            ])
            
            errors = [v for v in preview_result["audit"]["validations"] if v["kind"] == "error"]
            warnings = [v for v in preview_result["audit"]["validations"] if v["kind"] == "warning"]
            
            if errors:
                lines.append(f"**Errors:** {len(errors)}")
            if warnings:
                lines.append(f"**Warnings:** {len(warnings)}")
            if preview_result["audit"]["conflicts"]:
                lines.append(f"**Conflicts:** {len(preview_result['audit']['conflicts'])}")
        
        markdown_content = "\n".join(lines)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(markdown_content.encode()),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=report_{body.template}.md"
            }
        )


@router.post("/batch")
def batch_generate(templates: List[str], body: PreviewBody):
    """
    Generate multiple reports from same payload
    
    Args:
        templates: List of template IDs
        body: Preview request body
        
    Returns:
        Dictionary of template ID to rendered report
    """
    results = {}
    
    for template_id in templates:
        if template_id not in REGISTRY:
            results[template_id] = {"error": f"Unknown template '{template_id}'"}
            continue
        
        # Generate report for this template
        body.template = template_id
        try:
            results[template_id] = preview(body)
        except Exception as e:
            results[template_id] = {"error": str(e)}
    
    return results


# Health check endpoint
@router.get("/health")
def health_check():
    """Check if report generation service is healthy"""
    return {
        "status": "healthy",
        "templates_available": len(REGISTRY),
        "version": "1.0.0"
    }
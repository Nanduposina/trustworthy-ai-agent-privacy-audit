from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from app.schemas import AuditRequest, AuditReport
from app.agent import run_audit

app = FastAPI(title="Trustworthy AI Agent & Privacy Audit Platform",
    description="Educational demo for controlled AI-tool orchestration and heuristic privacy auditing.",
    version="0.1.0")
INDEX = Path(__file__).parent / "static" / "index.html"

@app.get("/health")
def health():
    return {"status": "ok", "service": "trustworthy-ai-privacy-audit"}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return HTMLResponse(INDEX.read_text(encoding="utf-8"))

@app.post("/api/audits", response_model=AuditReport)
def create_audit(request: AuditRequest):
    try:
        return run_audit(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Audit failed safely.") from exc

@app.post("/api/audits/export")
def export_audit_report(report: AuditReport):
    """Return a validated audit response as a UTF-8 JSON attachment."""
    return Response(
        content=report.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="audit-report.json"'},
    )

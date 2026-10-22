from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.schemas import (
    AuditHistoryPage,
    AuditHistorySummaryItem,
    AuditHistorySummaryPage,
    AuditReport,
    AuditRequest,
)
from app.agent import run_audit
from app.database import get_db
from app.models import AuditRecord
from app.ollama import configured_ai_analyzer

app = FastAPI(title="Trustworthy AI Agent & Privacy Audit Platform",
    description="Educational demo for controlled AI-tool orchestration and heuristic privacy auditing.",
    version="0.1.0")
INDEX = Path(__file__).parent / "static" / "index.html"

@app.get("/health")
def health():
    return {"status": "ok", "service": "trustworthy-ai-privacy-audit"}

@app.get("/api/status")
def service_status():
    analyzer = configured_ai_analyzer()
    return {
        "ai_provider": "ollama" if analyzer.enabled else "none",
        "ai_enabled": analyzer.enabled,
        "ai_model": analyzer.model_name if analyzer.enabled else None,
        # Retain the old fields for existing clients; cloud Gemini is disabled.
        "gemini_enabled": False,
        "gemini_model": None,
    }

@app.get("/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1 FROM audit_records LIMIT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Audit database is temporarily unavailable.") from exc
    return {"status": "ready", "database": "ok"}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return HTMLResponse(INDEX.read_text(encoding="utf-8"))

@app.post("/api/audits", response_model=AuditReport)
def create_audit(request: AuditRequest, db: Session = Depends(get_db)):
    try:
        report = run_audit(request)
        db.add(AuditRecord.from_report(report))
        db.commit()
        return report
    except SQLAlchemyError as exc:
        try:
            db.rollback()
        except SQLAlchemyError:
            pass
        raise HTTPException(status_code=503, detail="Audit database is temporarily unavailable.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Audit failed safely.") from exc

@app.get("/api/audits", response_model=AuditHistoryPage)
def list_audits(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
):
    try:
        total = db.scalar(select(func.count()).select_from(AuditRecord)) or 0
        records = db.scalars(
            select(AuditRecord)
            .order_by(AuditRecord.created_at.desc(), AuditRecord.audit_id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return AuditHistoryPage(
            total=total, limit=limit, offset=offset,
            items=[record.to_report() for record in records],
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Audit database is temporarily unavailable.") from exc


@app.get("/api/audits/summary", response_model=AuditHistorySummaryPage)
def list_audit_summaries(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
):
    """Return real history metadata without sending finding evidence to the dashboard."""
    try:
        total = db.scalar(select(func.count()).select_from(AuditRecord)) or 0
        rows = db.execute(
            select(
                AuditRecord.audit_id,
                AuditRecord.model_name,
                AuditRecord.created_at,
                AuditRecord.risk_level,
                AuditRecord.risk_score,
                AuditRecord.summary,
            )
            .order_by(AuditRecord.created_at.desc(), AuditRecord.audit_id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return AuditHistorySummaryPage(
            total=total,
            limit=limit,
            offset=offset,
            items=[AuditHistorySummaryItem(**row._mapping) for row in rows],
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Audit database is temporarily unavailable.") from exc

@app.get("/api/audits/{audit_id}", response_model=AuditReport)
def get_audit(audit_id: str, db: Session = Depends(get_db)):
    try:
        record = db.get(AuditRecord, audit_id)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Audit database is temporarily unavailable.") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Audit report not found.")
    return record.to_report()

@app.post("/api/audits/export")
def export_audit_report(report: AuditReport):
    """Return a validated audit response as a UTF-8 JSON attachment."""
    return Response(
        content=report.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="audit-report.json"'},
    )

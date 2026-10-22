"""Relational storage for completed audit reports."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.schemas import AuditReport


class AuditRecord(Base):
    __tablename__ = "audit_records"
    __table_args__ = (Index("ix_audit_records_created_id", "created_at", "audit_id"),)

    audit_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_rationale: Mapped[str] = mapped_column(String, nullable=False)
    findings: Mapped[list] = mapped_column(JSON, nullable=False)
    tools_used: Mapped[list] = mapped_column(JSON, nullable=False)
    trace: Mapped[list] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    disclaimer: Mapped[str] = mapped_column(String, nullable=False)
    ai_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    @classmethod
    def from_report(cls, report: AuditReport) -> "AuditRecord":
        data = report.model_dump(mode="json")
        data["created_at"] = report.created_at
        return cls(**data)

    def to_report(self) -> AuditReport:
        created_at = self.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return AuditReport(
            audit_id=self.audit_id,
            model_name=self.model_name,
            created_at=created_at,
            risk_level=self.risk_level,
            risk_score=self.risk_score,
            risk_rationale=self.risk_rationale,
            findings=self.findings,
            tools_used=self.tools_used,
            trace=self.trace,
            summary=self.summary,
            disclaimer=self.disclaimer,
            ai_analysis=self.ai_analysis,
        )

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

RiskLevel = Literal["low", "medium", "high"]

class AuditRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(default="demo-model", min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    sample_outputs: list[str] = Field(default_factory=list, max_length=100)
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    run_prompt_injection_scan: bool = True

class Finding(BaseModel):
    id: str
    category: str
    severity: RiskLevel
    score_contribution: int = Field(ge=0, le=4)
    title: str
    # `description` explains the evidence; `recommendation` is the mitigation.
    description: str
    evidence: str
    recommendation: str

class ToolTrace(BaseModel):
    tool_name: str
    status: Literal["success", "error"]
    duration_ms: float
    summary: str

class AuditReport(BaseModel):
    audit_id: str
    model_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=10)
    risk_rationale: str
    findings: list[Finding]
    tools_used: list[str]
    trace: list[ToolTrace]
    summary: str
    disclaimer: str = "Educational heuristic scan only; not a formal privacy or security assessment."

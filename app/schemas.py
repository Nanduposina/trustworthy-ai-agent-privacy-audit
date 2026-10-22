from datetime import datetime, timezone
import json
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

RiskLevel = Literal["low", "medium", "high"]
MAX_SAMPLE_CHARACTERS = 8_000
MAX_TOTAL_SAMPLE_CHARACTERS = 64_000
MAX_TOOL_ARGUMENTS_BYTES = 16_000

class AuditRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(default="demo-model", min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    sample_outputs: list[str] = Field(default_factory=list, max_length=100)
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    run_prompt_injection_scan: bool = True
    run_ai_analysis: bool = False
    # Accept the old request field during migration; it now opts into only
    # the configured local provider and can never select Gemini.
    run_gemini_analysis: bool | None = Field(default=None, exclude=True)

    @field_validator("sample_outputs")
    @classmethod
    def bound_sample_text(cls, samples: list[str]) -> list[str]:
        if any(len(sample) > MAX_SAMPLE_CHARACTERS for sample in samples):
            raise ValueError(f"Each sample output must be at most {MAX_SAMPLE_CHARACTERS} characters.")
        if sum(map(len, samples)) > MAX_TOTAL_SAMPLE_CHARACTERS:
            raise ValueError(f"Combined sample outputs must be at most {MAX_TOTAL_SAMPLE_CHARACTERS} characters.")
        return samples

    @field_validator("tool_arguments")
    @classmethod
    def bound_tool_arguments(cls, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            size = len(json.dumps(arguments, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except (TypeError, ValueError, RecursionError) as exc:
            raise ValueError("Tool arguments must be JSON serializable.") from exc
        if size > MAX_TOOL_ARGUMENTS_BYTES:
            raise ValueError(f"Tool arguments must be at most {MAX_TOOL_ARGUMENTS_BYTES} UTF-8 bytes.")
        return arguments

    @model_validator(mode="after")
    def accept_legacy_ai_opt_in(self):
        if self.run_gemini_analysis is not None and not self.run_ai_analysis:
            self.run_ai_analysis = self.run_gemini_analysis
        return self

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
    source: Literal["rules"] = "rules"


class AIFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: Literal["possible_personal_data", "prompt_injection_signal", "other_security_concern"]
    severity: RiskLevel
    explanation: str = Field(min_length=1, max_length=600)
    evidence: str = Field(min_length=1, max_length=300)
    recommendation: str = Field(min_length=1, max_length=500)


class AIAnalysis(BaseModel):
    status: Literal["completed", "skipped", "error"]
    enabled: bool
    # Keep "gemini" readable for historical reports already stored as JSON.
    provider: Literal["ollama", "none", "gemini"] | None = None
    model_name: str | None = None
    summary: str | None = Field(default=None, max_length=500)
    findings: list[AIFinding] = Field(default_factory=list, max_length=10)
    reason: str | None = Field(default=None, max_length=120)


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
    disclaimer: str = "Educational heuristic and optional AI-assisted scan only; not a formal privacy or security assessment."
    # None preserves compatibility with older persisted reports.
    ai_analysis: AIAnalysis | None = None

class AuditHistoryPage(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0, le=1_000_000)
    items: list[AuditReport]


class AuditHistorySummaryItem(BaseModel):
    """Small browser-facing summary that does not include report evidence."""
    audit_id: str
    model_name: str
    created_at: datetime
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=10)
    summary: str

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class AuditHistorySummaryPage(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0, le=1_000_000)
    items: list[AuditHistorySummaryItem]

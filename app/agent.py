import time
import uuid
from app.schemas import AIAnalysis, AuditRequest, AuditReport, Finding, ToolTrace
from app.tools import scan_sample_outputs, scan_prompt_injection, validate_tool_arguments
from app.ollama import configured_ai_analyzer

SEVERITY_POINTS = {"low": 1, "medium": 2, "high": 4}
MAX_RISK_SCORE = 10


def _count_label(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else plural or singular + 's'}"


def _risk_level(score: int) -> str:
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _risk_rationale(score: int) -> str:
    return (
        f"Rule-based severity points are low=1, medium=2, high=4 and sum to a maximum of "
        f"{MAX_RISK_SCORE}. Scores 0-1 are low, 2-3 medium, and 4-10 high. "
        f"This heuristic score is {score}; it is a prioritization aid, not a probability or compliance measure."
    )

def run_audit(request: AuditRequest, ai_analyzer=None) -> AuditReport:
    findings: list[Finding] = []
    trace: list[ToolTrace] = []
    tools_used: list[str] = []

    def execute(name, fn, *args):
        start = time.perf_counter()
        try:
            result = fn(*args)
            for raw in result.get("findings", []):
                severity = raw["severity"]
                findings.append(Finding(
                    id=f"F-{len(findings)+1:03d}",
                    score_contribution=SEVERITY_POINTS[severity],
                    **raw,
                ))
            summary = _count_label(len(result.get("findings", [])), "finding")
            if "valid" in result:
                summary += "; arguments " + ("valid" if result["valid"] else "rejected")
            trace.append(ToolTrace(tool_name=name, status="success",
                duration_ms=round((time.perf_counter()-start)*1000, 3), summary=summary))
        except Exception as exc:
            trace.append(ToolTrace(tool_name=name, status="error",
                duration_ms=round((time.perf_counter()-start)*1000, 3),
                summary=f"Tool failed safely: {type(exc).__name__}"))
        tools_used.append(name)

    execute("scan_sample_outputs", scan_sample_outputs, request.sample_outputs)
    if request.run_prompt_injection_scan:
        execute("scan_prompt_injection", scan_prompt_injection, request.sample_outputs)
    execute("validate_tool_arguments", validate_tool_arguments, request.tool_arguments)
    analyzer = ai_analyzer or configured_ai_analyzer()
    if request.run_ai_analysis:
        start = time.perf_counter()
        try:
            ai_analysis = analyzer.analyze(request.sample_outputs)
        except Exception:
            # Optional AI failure must never prevent deterministic findings or persistence.
            ai_analysis = AIAnalysis(
                status="error", enabled=analyzer.enabled,
                provider="ollama" if analyzer.enabled else "none",
                model_name=analyzer.model_name if analyzer.enabled else None,
                reason="request_failed",
            )
        trace.append(ToolTrace(
            tool_name="ollama_contextual_analysis",
            status="success" if ai_analysis.status != "error" else "error",
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            summary=("AI analysis " + ai_analysis.status +
                     (f" ({ai_analysis.reason})" if ai_analysis.reason else "")),
        ))
        tools_used.append("ollama_contextual_analysis")
    else:
        ai_analysis = AIAnalysis(
            status="skipped", enabled=analyzer.enabled,
            provider="ollama" if analyzer.enabled else "none",
            model_name=analyzer.model_name if analyzer.enabled else None,
            reason="not_requested" if analyzer.enabled else "not_configured",
        )
    risk_score = min(sum(item.score_contribution for item in findings), MAX_RISK_SCORE)
    risk = _risk_level(risk_score)
    sample_label = _count_label(len(request.sample_outputs), "sample output")
    tool_label = _count_label(len(tools_used), "tool")
    finding_label = _count_label(len(findings), "finding")
    return AuditReport(
        audit_id=str(uuid.uuid4()), model_name=request.name, risk_level=risk,
        risk_score=risk_score, risk_rationale=_risk_rationale(risk_score),
        findings=findings, tools_used=tools_used, trace=trace,
        summary=f"Scanned {sample_label} with {tool_label}. Detected {finding_label}; overall risk is {risk}.",
        ai_analysis=ai_analysis,
    )

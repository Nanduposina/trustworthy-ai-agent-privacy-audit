import re
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
INJECTION_MARKERS = (
    "ignore all previous instructions", "ignore all rules", "reveal secrets",
    "reveal the system prompt", "bypass your safety", "act as an unrestricted",
)
ALLOWED_ARGUMENTS = {"query", "limit", "language", "top_k", "document_id"}
MAX_LIMIT = 100
MAX_STRING_LENGTH = 500

def scan_sample_outputs(sample_outputs: list[str]) -> dict[str, Any]:
    findings = []
    for index, text in enumerate(sample_outputs):
        for match in EMAIL_RE.finditer(text):
            findings.append({
                "category": "possible_personal_data", "severity": "high",
                "title": "Email-like value in sample output",
                "description": "A sample output contains a string matching a common email format.",
                "evidence": f"sample_outputs[{index}]: {match.group(0)[:120]}",
                "recommendation": "Verify whether this is synthetic or personal data; redact or minimize it where appropriate."
            })
        for match in PHONE_RE.finditer(text):
            value = match.group(0).strip()
            if len(re.sub(r"\D", "", value)) >= 9:
                findings.append({
                    "category": "possible_personal_data", "severity": "medium",
                    "title": "Phone-like value in sample output",
                    "description": "A sample output contains a numeric string that may be a phone number.",
                    "evidence": f"sample_outputs[{index}]: {value[:120]}",
                    "recommendation": "Review the source and redact personal information if the value is genuine."
                })
    return {"findings": findings, "samples_scanned": len(sample_outputs)}

def scan_prompt_injection(sample_outputs: list[str]) -> dict[str, Any]:
    findings = []
    for index, text in enumerate(sample_outputs):
        lowered = text.lower()
        for marker in INJECTION_MARKERS:
            if marker in lowered:
                findings.append({
                    "category": "prompt_injection_signal", "severity": "medium",
                    "title": "Prompt-injection-like phrase detected",
                    "description": "The sample contains a phrase commonly associated with instruction override attempts.",
                    "evidence": f"sample_outputs[{index}]: {marker}",
                    "recommendation": "Treat text as untrusted data; separate instructions from content and test with a broader adversarial suite."
                })
                break
    return {"findings": findings, "samples_scanned": len(sample_outputs)}

def validate_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    issues = []
    for key, value in arguments.items():
        if key not in ALLOWED_ARGUMENTS:
            issues.append(f"Unknown argument: {key}")
            continue
        if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
            issues.append(f"Argument '{key}' exceeds {MAX_STRING_LENGTH} characters")
        if key in {"limit", "top_k"} and (
            not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > MAX_LIMIT
        ):
            issues.append(f"Argument '{key}' must be an integer between 1 and {MAX_LIMIT}")
    findings = []
    if issues:
        findings.append({
            "category": "unsafe_tool_arguments", "severity": "high",
            "title": "Tool arguments failed validation",
            "description": "One or more proposed arguments are outside the tool's allowlist or bounds.",
            "evidence": "; ".join(issues)[:500],
            "recommendation": "Reject unknown fields and enforce strict schemas and bounds before any tool executes."
        })
    return {"valid": not issues, "issues": issues, "findings": findings}

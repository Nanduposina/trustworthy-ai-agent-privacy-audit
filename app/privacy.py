"""Best-effort redaction helpers shared by optional analysis providers."""

import re

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
_CREDENTIAL_RE = re.compile(
    r"(?i)([\"']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"auth(?:orization)?|password|passwd|secret|client[_-]?secret)[\"']?\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^,\s}]+)"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_TOKEN_RE = re.compile(
    r"\b(?:AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9_-]{16,}|"
    r"gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]{16,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,})\b"
)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def redact_samples_for_ai(sample_outputs: list[str]) -> list[str]:
    """Redact common PII and credential patterns; this is not anonymization."""
    redacted: list[str] = []
    for sample in sample_outputs:
        value = _CREDENTIAL_RE.sub(r"\1[REDACTED_CREDENTIAL]", sample)
        value = _BEARER_RE.sub("Bearer [REDACTED_TOKEN]", value)
        value = _TOKEN_RE.sub("[REDACTED_TOKEN]", value)
        value = _JWT_RE.sub("[REDACTED_TOKEN]", value)
        value = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
        value = _PHONE_RE.sub("[REDACTED_PHONE]", value)
        redacted.append(value)
    return redacted

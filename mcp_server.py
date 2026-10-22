from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError
from app.tools import scan_sample_outputs, scan_prompt_injection, validate_tool_arguments
from app.schemas import AuditRequest, MAX_SAMPLE_CHARACTERS, MAX_TOTAL_SAMPLE_CHARACTERS

mcp = FastMCP("privacy-audit-tools")


def _validate_sample_limits(sample_outputs: list[str]) -> None:
    if len(sample_outputs) > 100:
        raise ValueError("At most 100 sample outputs are allowed.")
    if any(len(sample) > MAX_SAMPLE_CHARACTERS for sample in sample_outputs):
        raise ValueError(f"Each sample output must be at most {MAX_SAMPLE_CHARACTERS} characters.")
    if sum(map(len, sample_outputs)) > MAX_TOTAL_SAMPLE_CHARACTERS:
        raise ValueError(
            f"Combined sample outputs must be at most {MAX_TOTAL_SAMPLE_CHARACTERS} characters."
        )

@mcp.tool()
def scan_outputs(sample_outputs: list[str]) -> dict:
    """Scan sample model outputs for email-like and phone-like values."""
    _validate_sample_limits(sample_outputs)
    return scan_sample_outputs(sample_outputs)

@mcp.tool()
def scan_injection_signals(sample_outputs: list[str]) -> dict:
    """Flag common prompt-injection-like phrases in untrusted text."""
    _validate_sample_limits(sample_outputs)
    return scan_prompt_injection(sample_outputs)

@mcp.tool()
def check_tool_arguments(arguments: dict) -> dict:
    """Validate proposed tool arguments against an allowlist and conservative bounds."""
    if len(arguments) > 50:
        raise ValueError("At most 50 arguments are allowed.")
    try:
        AuditRequest(tool_arguments=arguments)
    except (ValidationError, TypeError, ValueError, RecursionError):
        raise ValueError("Tool arguments must be JSON serializable and within the size limit.") from None
    return validate_tool_arguments(arguments)

if __name__ == "__main__":
    mcp.run(transport="stdio")

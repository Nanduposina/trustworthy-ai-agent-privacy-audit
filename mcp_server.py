from mcp.server.fastmcp import FastMCP
from app.tools import scan_sample_outputs, scan_prompt_injection, validate_tool_arguments

mcp = FastMCP("privacy-audit-tools")

@mcp.tool()
def scan_outputs(sample_outputs: list[str]) -> dict:
    """Scan sample model outputs for email-like and phone-like values."""
    if len(sample_outputs) > 100:
        raise ValueError("At most 100 sample outputs are allowed.")
    return scan_sample_outputs(sample_outputs)

@mcp.tool()
def scan_injection_signals(sample_outputs: list[str]) -> dict:
    """Flag common prompt-injection-like phrases in untrusted text."""
    if len(sample_outputs) > 100:
        raise ValueError("At most 100 sample outputs are allowed.")
    return scan_prompt_injection(sample_outputs)

@mcp.tool()
def check_tool_arguments(arguments: dict) -> dict:
    """Validate proposed tool arguments against an allowlist and conservative bounds."""
    if len(arguments) > 50:
        raise ValueError("At most 50 arguments are allowed.")
    return validate_tool_arguments(arguments)

if __name__ == "__main__":
    mcp.run(transport="stdio")

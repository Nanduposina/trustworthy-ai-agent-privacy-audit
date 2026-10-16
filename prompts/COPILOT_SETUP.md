# VS Code Copilot setup prompts

Run these prompts one at a time.

1. **Inspect:** "Read README.md, requirements.txt, app/, mcp_server.py, and tests/. Explain the architecture and setup commands. Do not change files yet. Identify dependency/version issues."
2. **Environment and tests:** "Help me create a Python 3.11 virtual environment, install requirements.txt, and run pytest -q. If a command fails, explain the cause and propose the smallest fix. Do not remove tests."
3. **Run app:** "Start the FastAPI app using uvicorn app.main:app --reload. Verify /health, /, and /docs. Do not claim success unless we see successful responses."
4. **MCP compatibility:** "Check mcp_server.py against the installed official Python MCP SDK. Verify FastMCP import, tool signatures, and stdio transport. Make the smallest compatible change."
5. **Quality tooling:** "Add Ruff and mypy with reasonable configuration. Run them and fix genuine issues without weakening tests."
6. **Persistence:** "Add SQLite persistence for audit reports using SQLAlchemy. Do not persist raw sample outputs by default. Add tests and a retention/deletion approach."
7. **Optional LLM:** "Design an optional LLM planner interface while keeping deterministic mode as default. Validate every proposed tool call against a fixed allowlist and schemas. Never permit arbitrary shell commands or Python execution."
8. **Evaluation:** "Create labeled synthetic benchmark fixtures and report precision, recall, and F1 for each detector. Describe limitations and distinguish simulated results from real privacy guarantees."

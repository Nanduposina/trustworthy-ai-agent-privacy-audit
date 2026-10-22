# VS Code Copilot setup prompts

Run these prompts one at a time.

1. **Inspect:** "Read README.md, requirements.txt, app/, mcp_server.py, and tests/. Explain the architecture and setup commands. Do not change files yet. Identify dependency/version issues."
2. **Environment and tests:** "Help me create a Python 3.11 virtual environment, install requirements.txt, and run pytest -q. If a command fails, explain the cause and propose the smallest fix. Do not remove tests."
3. **Run app:** "Start the FastAPI app using uvicorn app.main:app --reload. Verify /health, /, and /docs. Do not claim success unless we see successful responses."
4. **MCP compatibility:** "Check mcp_server.py against the installed official Python MCP SDK. Verify FastMCP import, tool signatures, and stdio transport. Make the smallest compatible change."
5. **Quality tooling:** "Add Ruff and mypy with reasonable configuration. Run them and fix genuine issues without weakening tests."
6. **Persistence:** "Review the existing SQLAlchemy, PostgreSQL, and Alembic persistence. Preserve audit history and never reset or downgrade the database. Add tests using isolated SQLite fixtures."
7. **Optional local analysis:** "Review the optional local Ollama provider. Keep deterministic scoring authoritative, redact and bound inputs, validate model output, and never send samples to a cloud provider or execute model-generated instructions."
8. **Evaluation:** "Create labeled synthetic benchmark fixtures and report precision, recall, and F1 for each detector. Describe limitations and distinguish simulated results from real privacy guarantees."

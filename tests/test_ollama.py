import json

import httpx

from app.agent import run_audit
from app.ollama import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    MAX_RESPONSE_BYTES,
    MAX_VALIDATION_ATTEMPTS,
    OLLAMA_TIMEOUT_SECONDS,
    OllamaAnalyzer,
    _http_client,
    configured_ai_analyzer,
)
from app.schemas import AuditRequest


def structured_response(evidence="[REDACTED_EMAIL]"):
    return json.dumps({
        "summary": "Synthetic local analysis summary.",
        "findings": [{
            "category": "possible_personal_data",
            "severity": "medium",
            "explanation": "A contact-like value is present.",
            "evidence": evidence,
            "recommendation": "Use synthetic text in tests.",
        }],
    })


def analyzer_for(handler):
    transport = httpx.MockTransport(handler)
    timeouts = []

    def client_factory(timeout):
        timeouts.append(timeout)
        return httpx.Client(transport=transport, timeout=timeout)

    return OllamaAnalyzer(client_factory=client_factory), timeouts


def test_ollama_defaults_to_local_model_and_endpoint():
    analyzer = OllamaAnalyzer()
    assert analyzer.enabled is True
    assert analyzer.base_url == DEFAULT_OLLAMA_BASE_URL
    assert analyzer.model_name == DEFAULT_OLLAMA_MODEL


def test_ollama_http_client_ignores_proxy_environment(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(httpx, "Client", fake_client)
    _http_client(OLLAMA_TIMEOUT_SECONDS)
    assert captured["trust_env"] is False


def test_ollama_success_uses_json_schema_and_redacted_bounded_sample():
    secret_email = "synthetic.user@example.test"
    request_bodies = []

    def handler(request):
        request_bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": structured_response()}})

    analyzer, timeouts = analyzer_for(handler)
    result = analyzer.analyze([f"Contact {secret_email}"])

    assert result.status == "completed"
    assert result.provider == "ollama"
    assert result.model_name == "llama3.2:3b"
    assert result.findings[0].evidence == "[REDACTED_EMAIL]"
    assert len(request_bodies) == 1
    request = request_bodies[0]
    assert request["model"] == "llama3.2:3b"
    assert request["stream"] is False
    assert request["format"]["type"] == "object"
    assert request["options"] == {"temperature": 0, "num_predict": 512}
    assert secret_email not in request["messages"][0]["content"]
    assert "[REDACTED_EMAIL]" in request["messages"][0]["content"]
    assert timeouts == [OLLAMA_TIMEOUT_SECONDS]


def test_ollama_rejects_malformed_structured_response():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    analyzer, _ = analyzer_for(handler)
    result = analyzer.analyze(["Synthetic sample"])
    assert result.status == "error"
    assert result.reason == "invalid_model_json"
    assert result.findings == []
    assert len(requests) == MAX_VALIDATION_ATTEMPTS
    assert "not-json" not in result.model_dump_json()


def test_ollama_retries_one_malformed_response_then_accepts_valid_schema():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        content = "not-json" if len(requests) == 1 else structured_response("Synthetic sample")
        return httpx.Response(200, json={"message": {"content": content}})

    analyzer, _ = analyzer_for(handler)
    result = analyzer.analyze(["Synthetic sample"])

    assert result.status == "completed"
    assert result.findings[0].evidence == "Synthetic sample"
    assert len(requests) == 2
    assert "failed JSON/schema/evidence validation" in requests[1]["messages"][0]["content"]


def test_ollama_reports_schema_failure_after_bounded_retry_without_raw_output():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"message": {"content": json.dumps({"summary": "ok", "findings": [], "extra": "private model text"})}})

    analyzer, _ = analyzer_for(handler)
    result = analyzer.analyze(["Synthetic sample"])

    assert result.status == "error"
    assert result.reason == "invalid_model_schema"
    assert len(requests) == MAX_VALIDATION_ATTEMPTS
    assert "private model text" not in result.model_dump_json()


def test_ollama_rejects_evidence_not_present_in_redacted_sample():
    analyzer, _ = analyzer_for(
        lambda request: httpx.Response(
            200, json={"message": {"content": structured_response("invented evidence")}}
        )
    )
    result = analyzer.analyze(["Synthetic sample"])
    assert result.status == "error"
    assert result.reason == "unsupported_model_evidence"


def test_ollama_rejects_oversized_http_response():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))

    analyzer, _ = analyzer_for(handler)
    result = analyzer.analyze(["Synthetic sample"])
    assert result.status == "error"
    assert result.reason == "response_limit_exceeded"
    assert len(requests) == 1


def test_ollama_timeout_is_bounded_and_reported_safely():
    def handler(request):
        raise httpx.ReadTimeout("synthetic timeout detail", request=request)

    analyzer, timeouts = analyzer_for(handler)
    result = analyzer.analyze(["Synthetic sample"])
    assert result.status == "error"
    assert result.reason == "timeout"
    assert timeouts == [OLLAMA_TIMEOUT_SECONDS]
    assert "synthetic timeout detail" not in result.model_dump_json()


def test_ollama_unavailable_is_reported_without_provider_details():
    def handler(request):
        raise httpx.ConnectError("synthetic connection detail", request=request)

    analyzer, _ = analyzer_for(handler)
    result = analyzer.analyze(["Synthetic sample"])
    assert result.status == "error"
    assert result.reason == "service_unavailable"
    assert "synthetic connection detail" not in result.model_dump_json()


def test_ollama_failure_keeps_rule_findings_and_risk_score_authoritative():
    def handler(request):
        raise httpx.ConnectError("not reachable", request=request)

    analyzer, _ = analyzer_for(handler)
    report = run_audit(AuditRequest(
        sample_outputs=["Contact demo@example.test"],
        run_ai_analysis=True,
        tool_arguments={},
    ), ai_analyzer=analyzer)

    assert report.ai_analysis.status == "error"
    assert report.ai_analysis.reason == "service_unavailable"
    assert report.risk_score == 4
    assert len(report.findings) == 1
    assert report.findings[0].source == "rules"


def test_invalid_model_response_keeps_deterministic_audit_result():
    analyzer, _ = analyzer_for(
        lambda request: httpx.Response(200, json={"message": {"content": "not-json"}})
    )
    report = run_audit(AuditRequest(
        sample_outputs=["Contact demo@example.test"],
        run_ai_analysis=True,
        tool_arguments={},
    ), ai_analyzer=analyzer)

    assert report.ai_analysis.status == "error"
    assert report.ai_analysis.reason == "invalid_model_json"
    assert report.risk_score == 4
    assert len(report.findings) == 1
    assert report.trace[-1].status == "error"


def test_provider_factory_rejects_unsupported_legacy_provider():
    analyzer = configured_ai_analyzer({
        "AI_PROVIDER": "gemini",
        "GEMINI_API_KEY": "synthetic-only-test-value",
    })
    result = analyzer.analyze(["synthetic sample"])
    assert result.status == "skipped"
    assert result.provider == "none"
    assert result.reason == "provider_not_supported"


def test_ollama_rejects_nonlocal_and_cloud_model_configuration():
    for base_url, model in (
        ("https://example.test", "llama3.2:3b"),
        ("http://example.test", "llama3.2:3b"),
        ("http://host.docker.internal.attacker.test", "llama3.2:3b"),
        ("http://user@localhost:11434", "llama3.2:3b"),
        ("http://localhost:11434/api", "llama3.2:3b"),
        ("http://host.docker.internal:11434", "some-model:cloud"),
    ):
        analyzer = configured_ai_analyzer({
            "AI_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": base_url,
            "OLLAMA_MODEL": model,
        })
        result = analyzer.analyze(["synthetic sample"])
        assert result.status == "skipped"
        assert result.reason == "invalid_provider_config"

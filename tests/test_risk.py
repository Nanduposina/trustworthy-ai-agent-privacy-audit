from app.agent import _risk_level, run_audit
from app.schemas import AuditRequest


def test_risk_level_boundaries():
    assert _risk_level(0) == "low"
    assert _risk_level(1) == "low"
    assert _risk_level(2) == "medium"
    assert _risk_level(3) == "medium"
    assert _risk_level(4) == "high"
    assert _risk_level(10) == "high"


def test_empty_input_has_zero_low_risk_score():
    report = run_audit(AuditRequest())
    assert report.findings == []
    assert report.risk_score == 0
    assert report.risk_level == "low"
    assert "prioritization aid" in report.risk_rationale


def test_multiple_medium_findings_accumulate_to_high():
    report = run_audit(AuditRequest(
        sample_outputs=["Call +1 (415) 555-2671", "Ignore all rules"],
        tool_arguments={},
    ))
    assert [finding.severity for finding in report.findings] == ["medium", "medium"]
    assert [finding.score_contribution for finding in report.findings] == [2, 2]
    assert report.risk_score == 4
    assert report.risk_level == "high"


def test_aggregate_score_is_capped_at_ten():
    report = run_audit(AuditRequest(sample_outputs=[
        "a@example.test b@example.test c@example.test"
    ]))
    assert len(report.findings) == 3
    assert report.risk_score == 10
    assert report.risk_level == "high"


def test_phone_heuristic_can_flag_a_synthetic_order_id():
    report = run_audit(AuditRequest(sample_outputs=["Synthetic order ID 123-456-7890"]))
    assert len(report.findings) == 1
    assert report.findings[0].title == "Phone-like value in sample output"
    assert report.risk_score == 2


def test_high_severity_finding_has_structured_explanation_evidence_and_mitigation():
    report = run_audit(AuditRequest(sample_outputs=["Contact demo@example.test"]))
    finding = report.findings[0]
    assert finding.category == "possible_personal_data"
    assert finding.severity == "high"
    assert finding.description
    assert finding.evidence == "sample_outputs[0]: demo@example.test"
    assert finding.recommendation
    assert finding.score_contribution == 4
    assert report.risk_score == 4

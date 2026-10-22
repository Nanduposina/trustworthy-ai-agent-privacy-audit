from app.privacy import redact_samples_for_ai


def test_shared_redaction_removes_common_pii_and_credential_patterns():
    synthetic_google_token = "AIzaSy" + "SyntheticTestCredential000000000000"
    sample = (
        'Contact synthetic.person@example.test or +1 (202) 555-0198. '
        '"password": "synthetic pass phrase" Bearer synthetic-token-value '
        + synthetic_google_token
    )

    redacted = redact_samples_for_ai([sample])[0]

    assert "synthetic.person@example.test" not in redacted
    assert "202) 555-0198" not in redacted
    assert "synthetic pass phrase" not in redacted
    assert "synthetic-token-value" not in redacted
    assert synthetic_google_token not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_CREDENTIAL]" in redacted
    assert "[REDACTED_TOKEN]" in redacted

from triage.models.vulnerability import Vulnerability


def test_vulnerability_model() -> None:
    v = Vulnerability(
        id="vuln_01",
        type="SQL Injection",
        sink_line=18,
        source_line=44,
        message="Test message",
    )
    assert v.id == "vuln_01"
    assert v.type == "SQL Injection"
    assert v.sink_line == 18
    assert v.source_line == 44

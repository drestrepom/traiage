import json
from pathlib import Path

import pytest

from triage.models import load_findings, FindingsFile


def test_load_findings_valid(tmp_path: Path) -> None:
    data = {
        "vulnerabilities": [
            {
                "id": "v1",
                "type": "SQL Injection",
                "sink_line": 18,
                "source_line": 44,
                "message": "Test",
            }
        ]
    }
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = load_findings(path)
    assert isinstance(result, FindingsFile)
    assert len(result.vulnerabilities) == 1
    assert result.vulnerabilities[0].id == "v1"


def test_load_findings_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        load_findings(Path("/nonexistent/findings.json"))


def test_load_findings_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "findings.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_findings(path)

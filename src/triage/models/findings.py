import json
from pathlib import Path

from pydantic import BaseModel, Field

from triage.models.vulnerability import Vulnerability


class FindingsFile(BaseModel):
    vulnerabilities: list[Vulnerability] = Field(..., min_length=1)

    model_config = {"extra": "forbid"}


def load_findings(path: Path) -> FindingsFile:
    if not path.exists():
        raise FileNotFoundError(f"Findings file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in findings file: {e}") from e
    try:
        return FindingsFile.model_validate(data)
    except Exception as e:
        raise ValueError(f"Findings file does not match schema: {e}") from e

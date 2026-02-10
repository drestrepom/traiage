from pydantic import BaseModel, Field

from enum import Enum


class Verdict(Enum):
    TRUE_POSITIVE = "True Positive"
    FALSE_POSITIVE = "False Positive"
    NOT_EVALUATED = "not_evaluated"


class FindingResult(BaseModel):
    finding_id: str = Field(..., description="ID of the finding")
    verdict: Verdict = Field(..., description="Verdict of the finding")
    justification: str = Field(
        default="", description="Brief justification with code references"
    )
    error_message: str | None = Field(
        default=None, description="When verdict is not_evaluated, reason for failure"
    )


class ValidationReport(BaseModel):
    findings: list[FindingResult] = Field(..., description="Result per finding")

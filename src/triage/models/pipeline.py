from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from triage.models.vulnerability import Vulnerability


class CodeSnippet(BaseModel):
    file: str = Field(..., description="Relative path to file")
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    purpose: str = Field(default="", description="What this snippet is for")
    text: str = Field(default="", description="Snippet content")


class EntityRef(BaseModel):
    name: str | None = None
    file: str = Field(...)
    start_line: int | None = None
    end_line: int | None = None
    line: int | None = None
    code: str | None = None


class CallerInfo(BaseModel):
    callee: str = Field(...)
    caller_file: str = Field(...)
    caller_range: dict[str, int] = Field(default_factory=dict)
    notes: str = Field(default="")


class DataflowHypothesis(BaseModel):
    from_: str = Field(..., alias="from")
    to: str = Field(...)
    path_summary: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_snippets: list[CodeSnippet] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ValidatorCandidate(BaseModel):
    file: str = Field(...)
    line: int = Field(..., ge=1)
    code: str = Field(default="")


class EvidencePack(BaseModel):
    finding_id: str = Field(...)
    primary_file: str = Field(default="")
    snippets: list[CodeSnippet] = Field(default_factory=list)
    entities: dict[str, Any] = Field(
        default_factory=dict,
        description="suspected_function, sink, source as EntityRef or dict",
    )
    callers: list[CallerInfo] = Field(default_factory=list)
    dataflow_hypotheses: list[DataflowHypothesis] = Field(default_factory=list)
    validators_candidates: list[ValidatorCandidate] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class PathStep(BaseModel):
    file: str = Field(...)
    function: str = Field(default="")
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    code_excerpt: str = Field(default="")


class TraceResult(BaseModel):
    paths: list[PathStep] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class MitigationAssessment(BaseModel):
    sufficient: bool | None = None
    insufficient: bool | None = None
    unknown: bool | None = None
    rationale: str = Field(default="")
    citations: list[str] = Field(default_factory=list)


class MitigationsResult(BaseModel):
    mitigations_found: list[dict[str, Any]] = Field(default_factory=list)
    assessment_per_mitigation: list[MitigationAssessment] = Field(default_factory=list)


class AssumptionCategory(str, Enum):
    VERIFIABLE_STATIC = "A"
    NOT_VERIFIABLE_STATIC = "B"


class Assumption(BaseModel):
    text: str = Field(...)
    category: AssumptionCategory = Field(...)
    evidence_citations: list[str] = Field(default_factory=list)


class AssumptionsResult(BaseModel):
    assumptions: list[Assumption] = Field(default_factory=list)


class VerdictPipeline(str, Enum):
    TRUE_VULNERABILITY = "TRUE_VULNERABILITY"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INCONCLUSIVE = "INCONCLUSIVE"


class VerdictResult(BaseModel):
    verdict: VerdictPipeline = Field(...)
    reasoning: str = Field(default="")
    key_evidence: list[str] = Field(default_factory=list)
    remaining_unknowns: list[str] = Field(default_factory=list)


class Counterexample(BaseModel):
    type: str = Field(default="")
    explanation: str = Field(default="")
    citations: list[str] = Field(default_factory=list)


class CounterexampleResult(BaseModel):
    counterexample: Counterexample = Field(default_factory=Counterexample)
    fp_mechanism: str = Field(default="")


class SeverityResult(BaseModel):
    severity: str = Field(default="")
    priority: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = Field(default="")


class TriagePipelineReport(BaseModel):
    finding: Vulnerability = Field(...)
    verdict: VerdictResult = Field(...)
    evidence_pack: EvidencePack | None = Field(default=None)
    source_to_sink_trace: TraceResult | None = Field(default=None)
    sanitizers_validators: MitigationsResult | None = Field(default=None)
    explicit_assumptions: AssumptionsResult | None = Field(default=None)
    minimal_counterexample: CounterexampleResult | None = Field(default=None)
    severity_priority: SeverityResult | None = Field(default=None)
    open_questions: list[str] = Field(default_factory=list)


class PipelineReport(BaseModel):
    reports: list[TriagePipelineReport] = Field(
        ..., description="One report per finding"
    )

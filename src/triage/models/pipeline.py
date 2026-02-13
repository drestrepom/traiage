from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from triage.models.vulnerability import Vulnerability


class CodeSnippet(BaseModel):
    file: str = Field(..., description="Relative path to the file.")
    start_line: int = Field(..., ge=1, description="Start line (1-based).")
    end_line: int = Field(..., ge=1, description="End line (1-based).")
    purpose: str = Field(
        default="",
        description="Purpose of this snippet. Use markdown when necessary.",
    )
    text: str = Field(
        default="",
        description="Content of the snippet. Use markdown when necessary.",
    )


class EntityRef(BaseModel):
    name: str | None = Field(
        default=None, description="Name of the entity (function, variable, etc.)."
    )
    file: str = Field(..., description="Relative path to the file.")
    start_line: int | None = Field(default=None, description="Start line of the range.")
    end_line: int | None = Field(default=None, description="End line of the range.")
    line: int | None = Field(
        default=None, description="Single line when there is no range."
    )
    code: str | None = Field(
        default=None,
        description="Code excerpt or description. Use markdown when necessary.",
    )


class CallerInfo(BaseModel):
    callee: str = Field(..., description="Name of the called function or method.")
    caller_file: str = Field(
        ..., description="Relative path of the file where the call occurs."
    )
    caller_range: dict[str, int] = Field(
        default_factory=dict,
        description="Line range of the caller (e.g., start_line, end_line).",
    )
    notes: str = Field(
        default="",
        description="Notes about the caller. Use markdown when necessary.",
    )


class DataflowHypothesis(BaseModel):
    from_: str = Field(
        ...,
        alias="from",
        description="Origin of the dataflow (e.g., source, user input).",
    )
    to: str = Field(
        ...,
        description="Destination of the flow (e.g., vulnerable sink).",
    )
    path_summary: str = Field(
        default="",
        description="Summary of the dataflow path. Use markdown when necessary.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the hypothesis (0.0 to 1.0).",
    )
    supporting_snippets: list[CodeSnippet] = Field(
        default_factory=list,
        description="Code snippets supporting this dataflow hypothesis.",
    )

    model_config = {"populate_by_name": True}


class ValidatorCandidate(BaseModel):
    file: str = Field(
        ..., description="Relative path to the file where the validator exists."
    )
    line: int = Field(
        ..., ge=1, description="Line where the validator candidate appears."
    )
    code: str = Field(
        default="",
        description="Code excerpt or description. Use markdown when necessary.",
    )


class EvidencePack(BaseModel):
    finding_id: str = Field(..., description="Associated finding ID.")
    primary_file: str = Field(
        default="",
        description="Primary file where the evidence is concentrated.",
    )
    snippets: list[CodeSnippet] = Field(
        default_factory=list,
        description="Relevant code fragments (file, lines, purpose, text).",
    )
    entities: dict[str, Any] = Field(
        default_factory=dict,
        description="Key entities: suspected_function, sink, source (each as EntityRef or dict).",
    )
    callers: list[CallerInfo] = Field(
        default_factory=list,
        description="Relevant calls (callee, file, range, notes).",
    )
    dataflow_hypotheses: list[DataflowHypothesis] = Field(
        default_factory=list,
        description="Dataflow hypotheses from source to sink.",
    )
    validators_candidates: list[ValidatorCandidate] = Field(
        default_factory=list,
        description="Candidates for sanitizers/validators found in the path.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Open questions about missing evidence for the vulnerability (e.g. missing caller, source not found). Do NOT list metadata/tooling discrepancies (e.g. line number mismatches). Use markdown when necessary.",
    )


class PathStep(BaseModel):
    file: str = Field(..., description="Relative path to the file for this step.")
    function: str = Field(
        default="",
        description="Name of the function or scope for this step.",
    )
    start_line: int = Field(..., ge=1, description="Step start line (1-based).")
    end_line: int = Field(..., ge=1, description="Step end line (1-based).")
    code_excerpt: str = Field(
        default="",
        description="Code excerpt or step description. Use markdown when necessary.",
    )


class TraceResult(BaseModel):
    paths: list[PathStep] = Field(
        default_factory=list,
        description="Ordered trace steps from source to sink.",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Gaps or uncertainties in the trace. Use markdown when necessary.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the complete trace (0.0 to 1.0).",
    )


class MitigationAssessment(BaseModel):
    sufficient: bool | None = Field(
        default=None,
        description="True if mitigation is sufficient to block exploitation.",
    )
    insufficient: bool | None = Field(
        default=None,
        description="True if mitigation is not sufficient.",
    )
    unknown: bool | None = Field(
        default=None,
        description="True if it cannot be determined whether mitigation is sufficient.",
    )
    rationale: str = Field(
        default="",
        description="Reason why it is sufficient/insufficient. Use markdown when necessary.",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="References to code or lines supporting the assessment.",
    )


class MitigationsResult(BaseModel):
    mitigations_found: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of mitigations/sanitizers/validators found (each as dict).",
    )
    assessment_per_mitigation: list[MitigationAssessment] = Field(
        default_factory=list,
        description="Assessment (sufficient/insufficient/unknown + rationale) for each mitigation.",
    )


class AssumptionCategory(str, Enum):
    VERIFIABLE_STATIC = "A"
    NOT_VERIFIABLE_STATIC = "B"


class Assumption(BaseModel):
    text: str = Field(
        ...,
        description="Statement of the assumption. Use markdown when necessary.",
    )
    category: AssumptionCategory = Field(
        ...,
        description="A = statically verifiable; B = not statically verifiable.",
    )
    evidence_citations: list[str] = Field(
        default_factory=list,
        description="Citations or references supporting the assumption.",
    )


class AssumptionsResult(BaseModel):
    assumptions: list[Assumption] = Field(
        default_factory=list,
        description="List of explicit assumptions (text, category A/B, citations).",
    )


class VerdictPipeline(str, Enum):
    TRUE_VULNERABILITY = "TRUE_VULNERABILITY"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class VerdictResult(BaseModel):
    verdict: VerdictPipeline = Field(
        ...,
        description="Verdict: TRUE_VULNERABILITY, FALSE_POSITIVE.",
    )
    reasoning: str = Field(
        default="",
        description="Reasoning for the verdict. Use markdown when necessary.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the verdict (0.0 to 1.0).",
    )
    key_evidence: list[str] = Field(
        default_factory=list,
        description="Deprecated — fold into reasoning. Kept for JSON backward compat.",
    )
    remaining_unknowns: list[str] = Field(
        default_factory=list,
        description="Deprecated — fold into reasoning. Kept for JSON backward compat.",
    )


class Counterexample(BaseModel):
    type: str = Field(
        default="",
        description="Type of counterexample (e.g., constant variable, allowlist, parameterized query).",
    )
    explanation: str = Field(
        default="",
        description="Explanation of what condition breaks exploitability. Use markdown when necessary.",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="References to code or lines supporting the counterexample.",
    )


class CounterexampleResult(BaseModel):
    counterexample: Counterexample = Field(
        default_factory=Counterexample,
        description="Minimal counterexample (type, explanation, citations).",
    )
    fp_mechanism: str = Field(
        default="",
        description="Mechanism by which it is a false positive. Use markdown when necessary.",
    )


class SeverityResult(BaseModel):
    severity: str = Field(
        default="",
        description="Severity level (e.g., CVSS, Critical/High/Medium/Low).",
    )
    priority: str = Field(
        default="",
        description="Remediation priority (e.g., P1, P2, urgent).",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Kept for JSON backward compat. Verdict confidence is authoritative.",
    )
    rationale: str = Field(
        default="",
        description="Justification of severity/priority. Use markdown when necessary.",
    )
    suggested_fix: str = Field(
        default="",
        description="One-line recommended fix for the vulnerability.",
    )


class TriagePipelineReport(BaseModel):
    finding: Vulnerability = Field(
        ..., description="Original finding (id, type, file, lines, message)."
    )
    verdict: VerdictResult = Field(
        ...,
        description="Verdict and reasoning (verdict, reasoning, key_evidence, remaining_unknowns).",
    )
    evidence_pack: EvidencePack | None = Field(
        default=None,
        description="Evidence pack: snippets, entities, callers, dataflow hypotheses, validator candidates.",
    )
    source_to_sink_trace: TraceResult | None = Field(
        default=None,
        description="Trace from source to sink (paths, gaps, confidence).",
    )
    sanitizers_validators: MitigationsResult | None = Field(
        default=None,
        description="Sanitizers/validators found and assessment per mitigation.",
    )
    explicit_assumptions: AssumptionsResult | None = Field(
        default=None,
        description="Explicit assumptions (e.g., user-controlled input, safe parameterized query).",
    )
    minimal_counterexample: CounterexampleResult | None = Field(
        default=None,
        description="Minimal counterexample if verdict is FALSE_POSITIVE.",
    )
    severity_priority: SeverityResult | None = Field(
        default=None,
        description="Severity, priority and prioritization rationale.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Open questions from triage about the vulnerability or evidence. Do NOT list analysis metadata discrepancies. Use markdown when necessary.",
    )


class PipelineReport(BaseModel):
    reports: list[TriagePipelineReport] = Field(
        ...,
        description="One report per finding (each with finding, verdict, evidence, trace, assumptions, etc.).",
    )

"""Orchestrates pipeline agents A0–A6 for SAST triage."""

import json
import logging
from pathlib import Path
from typing import Any, Callable, TypeVar

from triage.agent.agents import (
    create_assumptions_extractor_agent,
    create_counterexample_builder_agent,
    create_evidence_collector_agent,
    create_sanitizers_analyzer_agent,
    create_severity_rater_agent,
    create_source_sink_tracer_agent,
    create_verdict_agent,
)
from triage.agent.deps import AgentDeps, PipelineDeps
from triage.models.pipeline import (
    AssumptionsResult,
    CounterexampleResult,
    EvidencePack,
    MitigationsResult,
    SeverityResult,
    TriagePipelineReport,
    TraceResult,
    VerdictPipeline,
    VerdictResult,
)
from triage.models.vulnerability import Vulnerability
from triage.utils.tree import find_function_node_for_line

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def _run_step(
    agent_factory: Callable[[], Any],
    deps: Any,
    user_prompt: str,
    step_name: str,
    fallback_factory: Callable[[Exception], T],
) -> T:
    """Run one pipeline agent; on exception log and return fallback_factory(e)."""
    agent = agent_factory()
    try:
        result = await agent.run(user_prompt, deps=deps)
        return result.output
    except Exception as e:
        logger.warning("%s failed: %s", step_name, e, exc_info=True)
        return fallback_factory(e)


def _build_a0_prompt(finding: Vulnerability, repo_root: Path) -> str:
    parts = [
        f"Repository: {repo_root}",
        f"Finding id: {finding.id}",
        f"Type: {finding.type}",
        f"sink_line: {finding.sink_line}, source_line: {finding.source_line}",
        f"Message: {finding.message}",
    ]
    node = find_function_node_for_line(Path(finding.file or ""), finding.sink_line)
    if node is not None:
        start_row, _ = node.start_point
        end_row, _ = node.end_point
        parts.append(f"Containing function: lines {start_row + 1}-{end_row + 1}")
    if finding.file:
        parts.append(f"Indicated file: {finding.file}")
    else:
        parts.append(
            "No file indicated: use the message and GREP to locate the function (e.g., def login) and the file."
        )
    return "\n".join(parts)


def is_evidence_sufficient(evidence_pack: EvidencePack, finding: Vulnerability) -> bool:
    """Deterministic gate: True if we have primary_file and sink/function covered."""
    if not evidence_pack.primary_file:
        return False
    if not evidence_pack.snippets:
        # Allow entities without snippets if sink/source are in entities
        entities = evidence_pack.entities or {}
        has_sink = "sink" in entities
        has_function = "suspected_function" in entities
        return has_sink or has_function
    # At least one snippet should cover the sink line or the function
    sink_ok = any(
        s.start_line <= finding.sink_line <= s.end_line for s in evidence_pack.snippets
    )
    if sink_ok:
        return True
    if evidence_pack.entities:
        return (
            "sink" in evidence_pack.entities
            or "suspected_function" in evidence_pack.entities
        )
    return False


def _to_markdown(data: Any, depth: int = 0) -> str:
    """Serialize dict/list to markdown (torsimany-style: headers for nesting, bullets for values)."""
    depth = min(depth, 5)  # cap at ######
    out: list[str] = []
    tab = "  "

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                prefix = "* " * (bool(depth)) + "#" * (depth + 1)
                out.append(f"{prefix} {str(k).title()} {'#' * (depth + 1)}\n")
                out.append(_to_markdown(v, depth + 1))
            else:
                indent = tab * (depth - 1) if depth else ""
                out.append(f"{indent}* {k}: {v}\n")
    elif isinstance(data, list):
        for i, v in enumerate(data):
            if not isinstance(v, (dict, list)):
                indent = tab * (depth - 1) if depth else ""
                out.append(f"{indent}* {i}: {v}\n")
            else:
                out.append(_to_markdown(v, depth))
    return "".join(out)


def _serialize_for_prompt(obj: Any) -> str:
    """Serialize object to markdown for use in prompts (torsimany-style)."""
    if obj is None:
        return "null"
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(exclude_none=True)
    else:
        data = json.loads(json.dumps(obj, default=str))
    return _to_markdown(data)


async def triage_finding(
    finding: Vulnerability,
    repo_path: Path,
    lsp: Any = None,
    model: str = "openai:gpt-5-mini",
) -> TriagePipelineReport:
    """Run the full pipeline for one finding; returns final report."""
    repo_path = repo_path.resolve()

    # --- A0 Evidence Collector ---
    evidence_pack = await _run_step(
        lambda: create_evidence_collector_agent(model=model),
        AgentDeps(repo_path=repo_path, vulnerability=finding, lsp=lsp),
        _build_a0_prompt(finding, repo_path),
        "A0 Evidence Collector",
        lambda e: EvidencePack(
            finding_id=finding.id,
            primary_file=finding.file or "",
            open_questions=[f"Error gathering evidence: {e}"],
        ),
    )

    # --- Gating ---
    if not is_evidence_sufficient(evidence_pack, finding):
        return TriagePipelineReport(
            finding=finding,
            verdict=VerdictResult(
                verdict=VerdictPipeline.INCONCLUSIVE,
                reasoning="Insufficient static evidence",
                confidence=0.0,
            ),
            evidence_pack=evidence_pack,
            open_questions=evidence_pack.open_questions or [],
        )

    # --- A1 Source→Sink Tracer ---
    trace = await _run_step(
        lambda: create_source_sink_tracer_agent(model=model),
        PipelineDeps(
            repo_path=repo_path,
            finding=finding,
            lsp=lsp,
            evidence_pack=evidence_pack,
        ),
        f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\nEvidence Pack:\n{_serialize_for_prompt(evidence_pack)}",
        "A1 Source-Sink Tracer",
        lambda e: TraceResult(paths=[], gaps=[str(e)], confidence=0.0),
    )

    # Optional early stop: very low confidence and no paths
    if trace.confidence < 0.3 and not trace.paths:
        verdict = await _run_step(
            lambda: create_verdict_agent(model=model),
            PipelineDeps(
                repo_path=repo_path,
                finding=finding,
                lsp=lsp,
                evidence_pack=evidence_pack,
                trace=trace,
                mitigations=None,
                assumptions=None,
            ),
            f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\nEvidence Pack:\n{_serialize_for_prompt(evidence_pack)}\n\nTrace (low confidence):\n{_serialize_for_prompt(trace)}",
            "A5 Verdict (early)",
            lambda e: VerdictResult(
                verdict=VerdictPipeline.INCONCLUSIVE,
                reasoning=str(e),
                confidence=0.0,
            ),
        )
        return build_final_report(
            finding=finding,
            verdict=verdict,
            evidence_pack=evidence_pack,
            trace=trace,
            mitigations=None,
            assumptions=None,
            counterexample=None,
            severity=None,
            open_questions=evidence_pack.open_questions or [],
        )

    # --- A2 Sanitizers Analyzer ---
    mitigations = await _run_step(
        lambda: create_sanitizers_analyzer_agent(model=model),
        PipelineDeps(
            repo_path=repo_path,
            finding=finding,
            lsp=lsp,
            evidence_pack=evidence_pack,
            trace=trace,
        ),
        f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\nEvidence Pack:\n{_serialize_for_prompt(evidence_pack)}\n\nTrace:\n{_serialize_for_prompt(trace)}",
        "A2 Sanitizers Analyzer",
        lambda e: MitigationsResult(),
    )

    # --- A3 Assumptions Extractor ---
    assumptions = await _run_step(
        lambda: create_assumptions_extractor_agent(model=model),
        PipelineDeps(
            repo_path=repo_path,
            finding=finding,
            lsp=lsp,
            evidence_pack=evidence_pack,
            trace=trace,
            mitigations=mitigations,
        ),
        f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\nEvidence Pack:\n{_serialize_for_prompt(evidence_pack)}\n\nTrace:\n{_serialize_for_prompt(trace)}\n\nMitigations:\n{_serialize_for_prompt(mitigations)}",
        "A3 Assumptions Extractor",
        lambda e: AssumptionsResult(),
    )

    # --- A5 Verdict ---
    verdict = await _run_step(
        lambda: create_verdict_agent(model=model),
        PipelineDeps(
            repo_path=repo_path,
            finding=finding,
            lsp=lsp,
            evidence_pack=evidence_pack,
            trace=trace,
            mitigations=mitigations,
            assumptions=assumptions,
        ),
        f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\nEvidence Pack:\n{_serialize_for_prompt(evidence_pack)}\n\nTrace:\n{_serialize_for_prompt(trace)}\n\nMitigations:\n{_serialize_for_prompt(mitigations)}\n\nAssumptions:\n{_serialize_for_prompt(assumptions)}",
        "A5 Verdict",
        lambda e: VerdictResult(
            verdict=VerdictPipeline.INCONCLUSIVE,
            reasoning=str(e),
            confidence=0.0,
        ),
    )

    counterexample: CounterexampleResult | None = None
    severity: SeverityResult | None = None

    if verdict.verdict == VerdictPipeline.FALSE_POSITIVE:
        counterexample = await _run_step(
            lambda: create_counterexample_builder_agent(model=model),
            PipelineDeps(
                repo_path=repo_path,
                finding=finding,
                lsp=lsp,
                evidence_pack=evidence_pack,
                trace=trace,
                mitigations=mitigations,
                assumptions=assumptions,
                verdict=verdict,
            ),
            f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\nEvidence Pack:\n{_serialize_for_prompt(evidence_pack)}\n\nTrace:\n{_serialize_for_prompt(trace)}\n\nMitigations:\n{_serialize_for_prompt(mitigations)}\n\nAssumptions:\n{_serialize_for_prompt(assumptions)}\n\nVerdict (FP):\n{_serialize_for_prompt(verdict)}",
            "A4 Counterexample Builder",
            lambda e: None,
        )

    elif verdict.verdict == VerdictPipeline.TRUE_VULNERABILITY:
        severity = await _run_step(
            lambda: create_severity_rater_agent(model=model),
            PipelineDeps(
                repo_path=repo_path,
                finding=finding,
                lsp=lsp,
                evidence_pack=evidence_pack,
                trace=trace,
                mitigations=mitigations,
                assumptions=assumptions,
                verdict=verdict,
            ),
            f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\nVerdict (True Vulnerability):\n{_serialize_for_prompt(verdict)}\n\nEvidence Pack:\n{_serialize_for_prompt(evidence_pack)}\n\nAssumptions:\n{_serialize_for_prompt(assumptions)}",
            "A6 Severity Rater",
            lambda e: None,
        )

    return build_final_report(
        finding=finding,
        verdict=verdict,
        evidence_pack=evidence_pack,
        trace=trace,
        mitigations=mitigations,
        assumptions=assumptions,
        counterexample=counterexample,
        severity=severity,
        open_questions=evidence_pack.open_questions or [],
    )


def build_final_report(
    finding: Vulnerability,
    verdict: VerdictResult,
    evidence_pack: EvidencePack | None = None,
    trace: TraceResult | None = None,
    mitigations: MitigationsResult | None = None,
    assumptions: AssumptionsResult | None = None,
    counterexample: CounterexampleResult | None = None,
    severity: SeverityResult | None = None,
    open_questions: list[str] | None = None,
) -> TriagePipelineReport:
    """Assemble the final pipeline report."""
    return TriagePipelineReport(
        finding=finding,
        verdict=verdict,
        evidence_pack=evidence_pack,
        source_to_sink_trace=trace,
        sanitizers_validators=mitigations,
        explicit_assumptions=assumptions,
        minimal_counterexample=counterexample,
        severity_priority=severity,
        open_questions=open_questions or [],
    )

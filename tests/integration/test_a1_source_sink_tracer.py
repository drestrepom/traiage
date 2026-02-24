"""Integration tests for A1 Source→Sink Tracer agent.

These tests use synthetic EvidencePack fixtures (pre-built in conftest.py)
to avoid calling A0 and focus solely on the tracer's output quality.

Skipped automatically when OPENAI_API_KEY is not set (see conftest.py).
"""

from __future__ import annotations

from triage.agent.agents import create_source_sink_tracer_agent
from triage.agent.deps import PipelineDeps
from triage.agent.orchestrator import _serialize_for_prompt
from triage.models.pipeline import TraceResult


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _run_a1(deps: PipelineDeps) -> TraceResult:
    agent = create_source_sink_tracer_agent()
    finding = deps.finding
    evidence = deps.evidence_pack
    prompt = (
        f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(evidence)}"
    )
    result = await agent.run(prompt, deps=deps)
    return result.output


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_a1_vuln01_confidence_above_threshold(
    pipeline_deps_a1_01: PipelineDeps,
) -> None:
    """A1 must produce confidence > 0.3 for the f-string SQL injection (early-stop threshold)."""
    trace = await _run_a1(pipeline_deps_a1_01)

    assert isinstance(trace, TraceResult)
    assert trace.confidence > 0.3, (
        f"confidence={trace.confidence} should be > 0.3 for a clear f-string injection"
    )


async def test_a1_paths_are_valid_path_steps(
    pipeline_deps_a1_01: PipelineDeps,
) -> None:
    """All PathSteps from A1 must have valid file names and line number ranges."""
    trace = await _run_a1(pipeline_deps_a1_01)

    assert trace.paths, "A1 should return at least one PathStep for vuln_01"
    for step in trace.paths:
        assert step.file, f"PathStep.file must be non-empty, got {step.file!r}"
        assert step.start_line >= 1, (
            f"PathStep.start_line={step.start_line} must be >= 1"
        )
        assert step.end_line >= step.start_line, (
            f"PathStep end_line={step.end_line} < start_line={step.start_line}"
        )


async def test_a1_vuln02_returns_trace_result(
    pipeline_deps_a1_02: PipelineDeps,
) -> None:
    """A1 must return a valid TraceResult with confidence in [0.0, 1.0] for vuln_02."""
    trace = await _run_a1(pipeline_deps_a1_02)

    assert isinstance(trace, TraceResult)
    assert 0.0 <= trace.confidence <= 1.0, (
        f"confidence={trace.confidence} out of [0.0, 1.0]"
    )

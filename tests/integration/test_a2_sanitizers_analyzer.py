"""Integration tests for A2 Sanitizers Analyzer agent.

Tests verify that A2 correctly identifies (or fails to find) mitigations
for canonical TP (vuln_01, f-string) and FP (vuln_02, parameterized) cases.

Skipped automatically when OPENAI_API_KEY is not set (see conftest.py).
"""

from __future__ import annotations

from triage.agent.agents import create_sanitizers_analyzer_agent
from triage.agent.deps import PipelineDeps
from triage.agent.orchestrator import _serialize_for_prompt
from triage.models.pipeline import MitigationsResult


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _run_a2(deps: PipelineDeps) -> MitigationsResult:
    agent = create_sanitizers_analyzer_agent()
    finding = deps.finding
    evidence = deps.evidence_pack
    trace = deps.trace
    prompt = (
        f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(evidence)}\n\n"
        f"Trace:\n{_serialize_for_prompt(trace)}"
    )
    result = await agent.run(prompt, deps=deps)
    return result.output


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_a2_vuln01_no_sufficient_mitigations(
    pipeline_deps_a2_01: PipelineDeps,
) -> None:
    """A2 must NOT find any sufficient mitigations for the unprotected f-string (vuln_01)."""
    mitigations = await _run_a2(pipeline_deps_a2_01)

    assert isinstance(mitigations, MitigationsResult)
    sufficient_count = sum(
        1
        for a in mitigations.assessment_per_mitigation
        if a.sufficient is True
    )
    assert sufficient_count == 0, (
        f"Expected 0 sufficient mitigations for vuln_01 f-string, got {sufficient_count}"
    )


async def test_a2_vuln02_finds_sufficient_mitigation(
    pipeline_deps_a2_02: PipelineDeps,
) -> None:
    """A2 must identify the parameterized query as a sufficient mitigation (vuln_02)."""
    mitigations = await _run_a2(pipeline_deps_a2_02)

    assert isinstance(mitigations, MitigationsResult)
    sufficient = [
        a for a in mitigations.assessment_per_mitigation if a.sufficient is True
    ]
    assert sufficient, (
        "Expected at least one sufficient mitigation for vuln_02 parameterized query"
    )


async def test_a2_assessment_has_at_least_one_flag(
    pipeline_deps_a2_02: PipelineDeps,
) -> None:
    """Each MitigationAssessment must have at least one of sufficient/insufficient/unknown set."""
    mitigations = await _run_a2(pipeline_deps_a2_02)

    for assessment in mitigations.assessment_per_mitigation:
        has_flag = (
            assessment.sufficient is not None
            or assessment.insufficient is not None
            or assessment.unknown is not None
        )
        assert has_flag, (
            f"MitigationAssessment has no flag set: {assessment!r}"
        )

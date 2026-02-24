"""Integration tests for A3 Assumptions Extractor agent.

Verifies structural validity of AssumptionsResult: at most 4 assumptions,
valid categories (A/B), non-empty assumption text.

Skipped automatically when OPENAI_API_KEY is not set (see conftest.py).
"""

from __future__ import annotations

from triage.agent.agents import create_assumptions_extractor_agent
from triage.agent.deps import PipelineDeps
from triage.agent.orchestrator import _serialize_for_prompt
from triage.models.pipeline import AssumptionCategory, AssumptionsResult


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _run_a3(deps: PipelineDeps) -> AssumptionsResult:
    agent = create_assumptions_extractor_agent()
    finding = deps.finding
    evidence = deps.evidence_pack
    trace = deps.trace
    mitigations = deps.mitigations
    prompt = (
        f"Finding:\n{_serialize_for_prompt(finding.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(evidence)}\n\n"
        f"Trace:\n{_serialize_for_prompt(trace)}\n\n"
        f"Mitigations:\n{_serialize_for_prompt(mitigations)}"
    )
    result = await agent.run(prompt, deps=deps)
    return result.output


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_a3_returns_at_most_4_assumptions(
    pipeline_deps_a3_01: PipelineDeps,
) -> None:
    """A3 must return at most 4 assumptions (per system prompt limit)."""
    result = await _run_a3(pipeline_deps_a3_01)

    assert isinstance(result, AssumptionsResult)
    assert len(result.assumptions) <= 4, (
        f"Expected <= 4 assumptions, got {len(result.assumptions)}"
    )


async def test_a3_categories_are_valid_enum(
    pipeline_deps_a3_01: PipelineDeps,
) -> None:
    """All assumptions must have a valid AssumptionCategory (A or B)."""
    result = await _run_a3(pipeline_deps_a3_01)

    valid_categories = {AssumptionCategory.VERIFIABLE_STATIC, AssumptionCategory.NOT_VERIFIABLE_STATIC}
    for assumption in result.assumptions:
        assert assumption.category in valid_categories, (
            f"Invalid category {assumption.category!r} — must be A or B"
        )


async def test_a3_assumption_text_nonempty(
    pipeline_deps_a3_01: PipelineDeps,
) -> None:
    """All assumption texts must be non-empty strings."""
    result = await _run_a3(pipeline_deps_a3_01)

    for assumption in result.assumptions:
        assert assumption.text.strip(), (
            f"Assumption text is empty: {assumption!r}"
        )

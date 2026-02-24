"""Integration tests for A5 Verdict Agent.

These are the most important integration tests: they verify that the agent
produces the correct TRUE_VULNERABILITY / FALSE_POSITIVE verdict for each
of the four canonical cases from sample1/sample.py.

Skipped automatically when OPENAI_API_KEY is not set (see conftest.py).
"""

from __future__ import annotations

from triage.agent.agents import create_verdict_agent
from triage.agent.deps import PipelineDeps
from triage.agent.orchestrator import _serialize_for_prompt
from triage.models.pipeline import VerdictPipeline, VerdictResult


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _run_a5(deps: PipelineDeps) -> VerdictResult:
    agent = create_verdict_agent()
    prompt = (
        f"Finding:\n{_serialize_for_prompt(deps.finding.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(deps.evidence_pack)}\n\n"
        f"Trace:\n{_serialize_for_prompt(deps.trace)}\n\n"
        f"Mitigations:\n{_serialize_for_prompt(deps.mitigations)}\n\n"
        f"Assumptions:\n{_serialize_for_prompt(deps.assumptions)}"
    )
    result = await agent.run(prompt, deps=deps)
    return result.output


# ---------------------------------------------------------------------------
# Verdict correctness tests
# ---------------------------------------------------------------------------


async def test_a5_vuln01_is_true_vulnerability(
    pipeline_deps_for_verdict_01: PipelineDeps,
) -> None:
    """A5 must return TRUE_VULNERABILITY for the f-string SQL injection (vuln_01)."""
    verdict = await _run_a5(pipeline_deps_for_verdict_01)

    assert verdict.verdict == VerdictPipeline.TRUE_VULNERABILITY, (
        f"Expected TRUE_VULNERABILITY for f-string SQL injection, "
        f"got {verdict.verdict}. Reasoning: {verdict.reasoning}"
    )


async def test_a5_vuln02_is_false_positive(
    pipeline_deps_for_verdict_02: PipelineDeps,
) -> None:
    """A5 must return FALSE_POSITIVE for the parameterized query (vuln_02)."""
    verdict = await _run_a5(pipeline_deps_for_verdict_02)

    assert verdict.verdict == VerdictPipeline.FALSE_POSITIVE, (
        f"Expected FALSE_POSITIVE for parameterized query, "
        f"got {verdict.verdict}. Reasoning: {verdict.reasoning}"
    )


async def test_a5_vuln03_ssrf_is_false_positive(
    pipeline_deps_for_verdict_03: PipelineDeps,
) -> None:
    """A5 must return FALSE_POSITIVE for the hardcoded-host SSRF (vuln_03).

    The system prompt includes an SSRF rule: a hardcoded host with only
    user-controlled path does not constitute a true SSRF vulnerability.
    """
    verdict = await _run_a5(pipeline_deps_for_verdict_03)

    assert verdict.verdict == VerdictPipeline.FALSE_POSITIVE, (
        f"Expected FALSE_POSITIVE for SSRF with hardcoded host, "
        f"got {verdict.verdict}. Reasoning: {verdict.reasoning}"
    )


async def test_a5_vuln04_cmdi_is_true_vulnerability(
    pipeline_deps_for_verdict_04: PipelineDeps,
) -> None:
    """A5 must return TRUE_VULNERABILITY for the os.system f-string injection (vuln_04)."""
    verdict = await _run_a5(pipeline_deps_for_verdict_04)

    assert verdict.verdict == VerdictPipeline.TRUE_VULNERABILITY, (
        f"Expected TRUE_VULNERABILITY for os.system command injection, "
        f"got {verdict.verdict}. Reasoning: {verdict.reasoning}"
    )


# ---------------------------------------------------------------------------
# Structural validity tests (use vuln_01 as representative)
# ---------------------------------------------------------------------------


async def test_a5_confidence_in_range(
    pipeline_deps_for_verdict_01: PipelineDeps,
) -> None:
    """A5 confidence must be in [0.0, 1.0]."""
    verdict = await _run_a5(pipeline_deps_for_verdict_01)

    assert 0.0 <= verdict.confidence <= 1.0, (
        f"confidence={verdict.confidence} out of [0.0, 1.0]"
    )


async def test_a5_reasoning_nonempty(
    pipeline_deps_for_verdict_01: PipelineDeps,
) -> None:
    """A5 must provide a non-empty reasoning string."""
    verdict = await _run_a5(pipeline_deps_for_verdict_01)

    assert verdict.reasoning.strip(), "A5 reasoning must not be empty"

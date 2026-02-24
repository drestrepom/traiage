"""Integration tests for A0 Evidence Collector agent.

These tests call the real LLM and verify that the agent returns
structurally valid EvidencePack objects for the canonical vuln_01,
vuln_02, and vuln_04 cases from sample1/sample.py.

Skipped automatically when OPENAI_API_KEY is not set (see conftest.py).
"""

from __future__ import annotations

from triage.agent.agents import create_evidence_collector_agent
from triage.agent.deps import AgentDeps
from triage.agent.orchestrator import _build_a0_prompt, is_evidence_sufficient
from triage.models.pipeline import EvidencePack
from triage.models.vulnerability import Vulnerability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_a0(deps: AgentDeps) -> EvidencePack:
    agent = create_evidence_collector_agent()
    prompt = _build_a0_prompt(deps.vulnerability, deps.repo_path)
    result = await agent.run(prompt, deps=deps)
    return result.output


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_a0_vuln01_returns_valid_pack(agent_deps_01: AgentDeps) -> None:
    """A0 must return a non-empty EvidencePack for the f-string SQL injection."""
    pack = await _run_a0(agent_deps_01)

    assert isinstance(pack, EvidencePack)
    assert pack.finding_id == "vuln_01"
    assert pack.primary_file, "primary_file must be set"


async def test_a0_vuln01_evidence_is_sufficient(
    agent_deps_01: AgentDeps,
    vuln_01: Vulnerability,
) -> None:
    """is_evidence_sufficient() must return True for vuln_01 after A0 runs."""
    pack = await _run_a0(agent_deps_01)
    assert is_evidence_sufficient(pack, vuln_01), (
        f"Evidence insufficient: primary_file={pack.primary_file!r}, "
        f"snippets={len(pack.snippets)}, entities={list(pack.entities.keys())}"
    )


async def test_a0_vuln02_returns_valid_pack(agent_deps_02: AgentDeps) -> None:
    """A0 must return a non-empty EvidencePack for the parameterized-query finding."""
    pack = await _run_a0(agent_deps_02)

    assert isinstance(pack, EvidencePack)
    assert pack.primary_file, "primary_file must be set"
    assert is_evidence_sufficient(pack, agent_deps_02.vulnerability)


async def test_a0_vuln04_returns_valid_pack(agent_deps_04: AgentDeps) -> None:
    """A0 must return a non-empty EvidencePack for the os.system command injection."""
    pack = await _run_a0(agent_deps_04)

    assert isinstance(pack, EvidencePack)
    assert pack.finding_id == "vuln_04"
    assert pack.primary_file, "primary_file must be set"


async def test_a0_snippet_lines_valid(agent_deps_01: AgentDeps) -> None:
    """All snippets from A0 must have valid line number ranges."""
    pack = await _run_a0(agent_deps_01)

    for snippet in pack.snippets:
        assert snippet.start_line >= 1, (
            f"snippet.start_line={snippet.start_line} must be >= 1"
        )
        assert snippet.end_line >= snippet.start_line, (
            f"snippet end_line={snippet.end_line} < start_line={snippet.start_line}"
        )


async def test_a0_confidence_in_range(agent_deps_01: AgentDeps) -> None:
    """All dataflow_hypotheses from A0 must have confidence in [0.0, 1.0]."""
    pack = await _run_a0(agent_deps_01)

    for hyp in pack.dataflow_hypotheses:
        assert 0.0 <= hyp.confidence <= 1.0, (
            f"confidence={hyp.confidence} out of [0.0, 1.0]"
        )

"""End-to-end integration tests for the full triage pipeline.

These tests call ``triage_finding()`` as a black box with the four canonical
vulnerabilities from sample1/sample.py and verify that:
  - The pipeline completes without raising
  - The verdict is correct
  - Post-verdict fields are populated appropriately (severity for TP, counterexample for FP)

Skipped automatically when OPENAI_API_KEY is not set (see conftest.py).
"""

from __future__ import annotations

from pathlib import Path

from triage.agent.orchestrator import triage_finding
from triage.models.pipeline import TriagePipelineReport, VerdictPipeline
from triage.models.vulnerability import Vulnerability

SAMPLE1_PATH = Path(__file__).resolve().parent.parent.parent / "samples" / "sample1"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_pipeline_vuln01_sqli_login(vuln_01: Vulnerability, lsp_session) -> None:  # type: ignore[no-untyped-def]
    """Full pipeline must classify the f-string SQL injection as TRUE_VULNERABILITY."""
    report = await triage_finding(vuln_01, SAMPLE1_PATH, lsp=lsp_session)

    assert isinstance(report, TriagePipelineReport)
    assert report.verdict.verdict == VerdictPipeline.TRUE_VULNERABILITY, (
        f"Expected TRUE_VULNERABILITY for vuln_01, got {report.verdict.verdict}. "
        f"Reasoning: {report.verdict.reasoning}"
    )
    # Severity should be populated for TRUE_VULNERABILITY
    assert report.severity_priority is not None, (
        "severity_priority must be set for a TRUE_VULNERABILITY"
    )
    # No counterexample for TRUE_VULNERABILITY
    assert report.minimal_counterexample is None, (
        "minimal_counterexample should be None for TRUE_VULNERABILITY"
    )


async def test_pipeline_vuln02_sqli_new_login(vuln_02: Vulnerability, lsp_session) -> None:  # type: ignore[no-untyped-def]
    """Full pipeline must classify the parameterized query as FALSE_POSITIVE."""
    report = await triage_finding(vuln_02, SAMPLE1_PATH, lsp=lsp_session)

    assert isinstance(report, TriagePipelineReport)
    assert report.verdict.verdict == VerdictPipeline.FALSE_POSITIVE, (
        f"Expected FALSE_POSITIVE for vuln_02, got {report.verdict.verdict}. "
        f"Reasoning: {report.verdict.reasoning}"
    )
    # Counterexample should be populated for FALSE_POSITIVE
    assert report.minimal_counterexample is not None, (
        "minimal_counterexample must be set for a FALSE_POSITIVE"
    )
    # Severity should not be set for FALSE_POSITIVE
    assert report.severity_priority is None, (
        "severity_priority should be None for FALSE_POSITIVE"
    )


async def test_pipeline_vuln03_ssrf(vuln_03: Vulnerability, lsp_session) -> None:  # type: ignore[no-untyped-def]
    """Full pipeline must classify the hardcoded-host SSRF as FALSE_POSITIVE."""
    report = await triage_finding(vuln_03, SAMPLE1_PATH, lsp=lsp_session)

    assert isinstance(report, TriagePipelineReport)
    assert report.verdict.verdict == VerdictPipeline.FALSE_POSITIVE, (
        f"Expected FALSE_POSITIVE for vuln_03 SSRF, got {report.verdict.verdict}. "
        f"Reasoning: {report.verdict.reasoning}"
    )
    # Structural validity: evidence_pack must be present
    assert report.evidence_pack is not None


async def test_pipeline_vuln04_cmdi(vuln_04: Vulnerability, lsp_session) -> None:  # type: ignore[no-untyped-def]
    """Full pipeline must classify the os.system command injection as FALSE_POSITIVE.

    demo() in sample.py does not call is_online_username() — there is no static
    dataflow from input() to os.system(). The pipeline correctly identifies this
    as FALSE_POSITIVE because no callsite connects demo() to is_online_username().
    """
    report = await triage_finding(vuln_04, SAMPLE1_PATH, lsp=lsp_session)

    assert isinstance(report, TriagePipelineReport)
    assert report.verdict.verdict == VerdictPipeline.FALSE_POSITIVE, (
        f"Expected FALSE_POSITIVE for vuln_04, got {report.verdict.verdict}. "
        f"Reasoning: {report.verdict.reasoning}"
    )
    assert report.minimal_counterexample is not None, (
        "minimal_counterexample must be set for a FALSE_POSITIVE"
    )
    assert report.severity_priority is None, (
        "severity_priority should be None for a FALSE_POSITIVE"
    )

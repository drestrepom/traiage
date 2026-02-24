"""LLM Judge evals for the A0 Evidence Collector agent.

Evaluates three quality dimensions of A0's output:
  1. Relevance: snippets cover the sink_line; primary_file matches the finding
  2. No hallucination: code patterns are consistent with real Python/SQLite code
  3. Quality of open_questions: questions address causal evidence, not metadata

Run:
    OPENAI_API_KEY=sk-... uv run pytest tests/evals/eval_evidence_collector.py -v -s
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from triage.agent.agents import create_evidence_collector_agent
from triage.agent.deps import AgentDeps
from triage.agent.orchestrator import _build_a0_prompt
from triage.agent.tools import start_lsp_client
from triage.models.pipeline import EvidencePack
from triage.models.vulnerability import Vulnerability

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE1_PATH = Path(__file__).resolve().parent.parent.parent / "samples" / "sample1"
_JUDGE_MODEL = "openai:gpt-5-mini"

# ---------------------------------------------------------------------------
# Vulnerability definitions
# ---------------------------------------------------------------------------

_VULNS: dict[str, Vulnerability] = {
    "vuln_01": Vulnerability(
        id="vuln_01",
        type="SQL Injection",
        sink_line=17,
        source_line=44,
        message="The application is vulnerable to SQL Injection in the login function",
        file="sample.py",
    ),
    "vuln_02": Vulnerability(
        id="vuln_02",
        type="SQL Injection",
        sink_line=27,
        source_line=44,
        message="The application is vulnerable to SQL Injection in the new_login function",
        file="sample.py",
    ),
}

# ---------------------------------------------------------------------------
# Task function
# ---------------------------------------------------------------------------


async def _run_evidence_collector(inputs: dict[str, object]) -> str:
    """Run A0 and return a JSON-serializable summary of the EvidencePack."""
    vuln = inputs["vuln"]
    prompt = _build_a0_prompt(vuln, SAMPLE1_PATH)  # type: ignore[arg-type]

    agent = create_evidence_collector_agent()
    async with start_lsp_client(SAMPLE1_PATH) as lsp:
        deps = AgentDeps(repo_path=SAMPLE1_PATH, lsp=lsp, vulnerability=vuln)  # type: ignore[arg-type]
        result = await agent.run(prompt, deps=deps)
    pack: EvidencePack = result.output

    # Serialize to a compact JSON string for the judge to evaluate
    summary = {
        "finding_id": pack.finding_id,
        "primary_file": pack.primary_file,
        "num_snippets": len(pack.snippets),
        "snippet_ranges": [
            {"file": s.file, "start_line": s.start_line, "end_line": s.end_line}
            for s in pack.snippets
        ],
        "entity_keys": list(pack.entities.keys()),
        "num_dataflow_hypotheses": len(pack.dataflow_hypotheses),
        "dataflow_confidences": [h.confidence for h in pack.dataflow_hypotheses],
        "open_questions": pack.open_questions,
        "snippet_texts": [s.text[:200] for s in pack.snippets],  # Truncated for judge
    }
    return json.dumps(summary, indent=2)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

evidence_dataset: Dataset[dict[str, object], str, None] = Dataset(
    cases=[
        Case(
            name="vuln_01_sqli_fstring",
            inputs={"vuln": _VULNS["vuln_01"], "sink_line": 17, "file": "sample.py"},
            expected_output=(
                "primary_file=sample.py, snippets cover lines around 15-22, "
                "entities include sink or suspected_function"
            ),
        ),
        Case(
            name="vuln_02_sqli_parameterized",
            inputs={"vuln": _VULNS["vuln_02"], "sink_line": 27, "file": "sample.py"},
            expected_output=(
                "primary_file=sample.py, snippets cover lines around 24-31, "
                "entities include sink or suspected_function"
            ),
        ),
    ],
    evaluators=[
        LLMJudge(
            rubric=(
                "The evidence pack output (JSON) satisfies all of the following:\n"
                "1. primary_file is 'sample.py' (matches the finding file).\n"
                "2. At least one snippet has start_line and end_line that bracket "
                "or are close to the sink_line provided in the input "
                "(within a reasonable function boundary, e.g. ±10 lines).\n"
                "3. entity_keys includes at least one of: 'sink', 'suspected_function', 'source'.\n"
                "If any of these conditions fail, the evaluation fails."
            ),
            include_input=True,
            include_expected_output=True,
            model=_JUDGE_MODEL,
        ),
        LLMJudge(
            rubric=(
                "The snippet_texts in the evidence pack output are consistent with "
                "real Python code using sqlite3 or requests libraries — they should "
                "contain recognizable Python constructs (def, cur.execute, f-string, etc.). "
                "The snippets must NOT contain invented function names, imports, "
                "or code patterns that are inconsistent with a simple Flask/SQLite app. "
                "Fail if the snippets look hallucinated or unrelated to SQL/HTTP operations."
            ),
            include_input=False,
            include_expected_output=False,
            model=_JUDGE_MODEL,
        ),
        LLMJudge(
            rubric=(
                "If the evidence pack has open_questions (list may be empty), "
                "each question must address missing *causal evidence* — for example, "
                "'Could not find the caller of login()' or 'Source of username is unclear'. "
                "Questions must NOT ask about line number discrepancies, metadata mismatches, "
                "or tool-level issues. Empty open_questions list always passes this rubric."
            ),
            include_input=False,
            include_expected_output=False,
            model=_JUDGE_MODEL,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pytest test
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def require_openai_key_evals() -> None:  # type: ignore[return]
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — skipping eval tests")


async def test_evidence_collector_eval_quality() -> None:
    """LLM judge eval: A0 evidence relevance and quality for vuln_01 and vuln_02."""
    report = await evidence_dataset.evaluate(_run_evidence_collector, max_concurrency=2)
    report.print(include_reasons=True)

    for case_result in report.cases:
        for assertion_name, assertion in case_result.assertions.items():
            assert assertion.value, (
                f"LLM judge failed for case '{case_result.trace_id}' "
                f"evaluator '{assertion_name}': {assertion.reason}"
            )

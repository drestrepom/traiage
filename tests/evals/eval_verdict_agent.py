"""LLM Judge evals for the A5 Verdict Agent.

Evaluates the *quality* of the agent's reasoning — not just structural
correctness — using pydantic-evals Dataset + LLMJudge.

Two rubrics per case:
  1. Verdict match + evidence citation quality
  2. Confidence coherence with evidence strength

Run:
    OPENAI_API_KEY=sk-... uv run pytest tests/evals/eval_verdict_agent.py -v -s
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from triage.agent.agents import create_verdict_agent
from triage.agent.deps import PipelineDeps
from triage.agent.orchestrator import _serialize_for_prompt
from triage.models.pipeline import (
    Assumption,
    AssumptionCategory,
    AssumptionsResult,
    CallerInfo,
    CodeSnippet,
    DataflowHypothesis,
    EvidencePack,
    MitigationAssessment,
    MitigationsResult,
    PathStep,
    TraceResult,
    VerdictResult,
)
from triage.models.vulnerability import Vulnerability

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE1_PATH = Path(__file__).resolve().parent.parent.parent / "samples" / "sample1"
_JUDGE_MODEL = "openai:gpt-5-mini"

# ---------------------------------------------------------------------------
# Build canonical inputs
# ---------------------------------------------------------------------------


def _make_deps_01() -> tuple[PipelineDeps, str]:
    """vuln_01 — SQL injection f-string → TRUE_VULNERABILITY."""
    vuln = Vulnerability(
        id="vuln_01",
        type="SQL Injection",
        sink_line=17,
        source_line=44,
        message="The application is vulnerable to SQL Injection in the login function",
        file="sample.py",
    )
    evidence = EvidencePack(
        finding_id="vuln_01",
        primary_file="sample.py",
        snippets=[
            CodeSnippet(
                file="sample.py",
                start_line=15,
                end_line=22,
                purpose="login() with f-string SQL injection at line 18",
                text=(
                    "def login(con, username, password):\n"
                    " cur = con.cursor()\n"
                    " # Consulta usuarios\n"
                    " sql_query = f\"SELECT id FROM users WHERE username = '{username}'"
                    " AND password = '{password}'\"\n"
                    " cur.execute(sql_query)\n"
                    " return cur.fetchone()\n"
                ),
            )
        ],
        entities={"sink": {"name": "cur.execute", "file": "sample.py", "line": 19}},
        dataflow_hypotheses=[
            DataflowHypothesis(
                **{
                    "from": "input() at demo() line 44 → username",
                    "to": "f-string interpolation → cur.execute(sql_query)",
                    "path_summary": "input() → login() → f-string → execute",
                    "confidence": 0.95,
                }
            )
        ],
    )
    trace = TraceResult(
        paths=[
            PathStep(
                file="sample.py",
                function="demo",
                start_line=44,
                end_line=44,
                code_excerpt='username = input("Username: ")',
            ),
            PathStep(
                file="sample.py",
                function="login",
                start_line=15,
                end_line=19,
                code_excerpt="sql_query = f\"SELECT ... WHERE username = '{username}' ...\"",
            ),
        ],
        gaps=[],
        confidence=0.95,
    )
    mitigations = MitigationsResult()
    assumptions = AssumptionsResult(
        assumptions=[
            Assumption(
                text="username/password originate from input() in demo(), no sanitization applied.",
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:18", "sample.py:44"],
            )
        ]
    )
    deps = PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln,
        evidence_pack=evidence,
        trace=trace,
        mitigations=mitigations,
        assumptions=assumptions,
    )
    prompt = (
        f"Finding:\n{_serialize_for_prompt(vuln.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(evidence)}\n\n"
        f"Trace:\n{_serialize_for_prompt(trace)}\n\n"
        f"Mitigations:\n{_serialize_for_prompt(mitigations)}\n\n"
        f"Assumptions:\n{_serialize_for_prompt(assumptions)}"
    )
    return deps, prompt


def _make_deps_02() -> tuple[PipelineDeps, str]:
    """vuln_02 — parameterized query → FALSE_POSITIVE."""
    vuln = Vulnerability(
        id="vuln_02",
        type="SQL Injection",
        sink_line=27,
        source_line=44,
        message="The application is vulnerable to SQL Injection in the new_login function",
        file="sample.py",
    )
    evidence = EvidencePack(
        finding_id="vuln_02",
        primary_file="sample.py",
        snippets=[
            CodeSnippet(
                file="sample.py",
                start_line=24,
                end_line=31,
                purpose="new_login() with safe parameterized query",
                text=(
                    "def new_login(con, username, password):\n"
                    " cur = con.cursor()\n"
                    " cur.execute(\n"
                    '  "SELECT id FROM users WHERE username = ? AND password = ?",\n'
                    "  (username, password)\n"
                    " )\n"
                    " return cur.fetchone()\n"
                ),
            )
        ],
        entities={"sink": {"name": "cur.execute", "file": "sample.py", "line": 27}},
        dataflow_hypotheses=[
            DataflowHypothesis(
                **{
                    "from": "input() at demo() line 44 → username, password",
                    "to": "parameterized cur.execute(query, (username, password))",
                    "path_summary": "input() → new_login() → parameterized execute (safe)",
                    "confidence": 0.85,
                }
            )
        ],
    )
    trace = TraceResult(
        paths=[
            PathStep(
                file="sample.py",
                function="demo",
                start_line=44,
                end_line=44,
                code_excerpt='username = input("Username: ")',
            ),
            PathStep(
                file="sample.py",
                function="new_login",
                start_line=24,
                end_line=30,
                code_excerpt='cur.execute("SELECT ... ? AND ?", (username, password))',
            ),
        ],
        gaps=["Input passes as tuple parameter, not string-interpolated"],
        confidence=0.85,
    )
    mitigations = MitigationsResult(
        mitigations_found=[
            {"type": "parameterized_query", "file": "sample.py", "line": 27}
        ],
        assessment_per_mitigation=[
            MitigationAssessment(
                sufficient=True,
                rationale="DB-API 2.0 parameterized query prevents injection.",
                citations=["sample.py:27"],
            )
        ],
    )
    assumptions = AssumptionsResult(
        assumptions=[
            Assumption(
                text="DB-API 2.0 driver correctly prevents injection with parameterized queries.",
                category=AssumptionCategory.NOT_VERIFIABLE_STATIC,
                evidence_citations=["sample.py:27"],
            )
        ]
    )
    deps = PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln,
        evidence_pack=evidence,
        trace=trace,
        mitigations=mitigations,
        assumptions=assumptions,
    )
    prompt = (
        f"Finding:\n{_serialize_for_prompt(vuln.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(evidence)}\n\n"
        f"Trace:\n{_serialize_for_prompt(trace)}\n\n"
        f"Mitigations:\n{_serialize_for_prompt(mitigations)}\n\n"
        f"Assumptions:\n{_serialize_for_prompt(assumptions)}"
    )
    return deps, prompt


def _make_deps_03() -> tuple[PipelineDeps, str]:
    """vuln_03 — SSRF hardcoded host → FALSE_POSITIVE."""
    vuln = Vulnerability(
        id="vuln_03",
        type="SSRF",
        sink_line=34,
        source_line=44,
        message="The application is vulnerable to SSRF in the check_username function",
        file="sample.py",
    )
    evidence = EvidencePack(
        finding_id="vuln_03",
        primary_file="sample.py",
        snippets=[
            CodeSnippet(
                file="sample.py",
                start_line=33,
                end_line=35,
                purpose="check_username() with hardcoded api.github.com host",
                text=(
                    "def check_username(username):\n"
                    ' response = requests.get(f"https://api.github.com/users/{username}")\n'
                    " return response\n"
                ),
            )
        ],
        entities={"sink": {"name": "requests.get", "file": "sample.py", "line": 34}},
        dataflow_hypotheses=[
            DataflowHypothesis(
                **{
                    "from": "input() at demo() line 44 → username",
                    "to": "path in requests.get(f'https://api.github.com/users/{username}')",
                    "path_summary": "input() → check_username() → requests.get (host hardcoded)",
                    "confidence": 0.80,
                }
            )
        ],
    )
    trace = TraceResult(
        paths=[
            PathStep(
                file="sample.py",
                function="demo",
                start_line=44,
                end_line=44,
                code_excerpt='username = input("Username: ")',
            ),
            PathStep(
                file="sample.py",
                function="check_username",
                start_line=33,
                end_line=34,
                code_excerpt='requests.get(f"https://api.github.com/users/{username}")',
            ),
        ],
        gaps=["Host is hardcoded — only URL path is user-controlled"],
        confidence=0.75,
    )
    mitigations = MitigationsResult(
        mitigations_found=[{"type": "hardcoded_host", "file": "sample.py", "line": 34}],
        assessment_per_mitigation=[
            MitigationAssessment(
                sufficient=True,
                rationale="Host is hardcoded — user cannot redirect to arbitrary server.",
                citations=["sample.py:34"],
            )
        ],
    )
    assumptions = AssumptionsResult(
        assumptions=[
            Assumption(
                text="The host 'api.github.com' is hardcoded and cannot be influenced by user input.",
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:34"],
            )
        ]
    )
    deps = PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln,
        evidence_pack=evidence,
        trace=trace,
        mitigations=mitigations,
        assumptions=assumptions,
    )
    prompt = (
        f"Finding:\n{_serialize_for_prompt(vuln.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(evidence)}\n\n"
        f"Trace:\n{_serialize_for_prompt(trace)}\n\n"
        f"Mitigations:\n{_serialize_for_prompt(mitigations)}\n\n"
        f"Assumptions:\n{_serialize_for_prompt(assumptions)}"
    )
    return deps, prompt


def _make_deps_04() -> tuple[PipelineDeps, str]:
    """vuln_04 — os.system f-string command injection → TRUE_VULNERABILITY."""
    vuln = Vulnerability(
        id="vuln_04",
        type="Command Injection",
        sink_line=39,
        source_line=44,
        message="The application is vulnerable to Command Injection in the is_online_username function",
        file="sample.py",
    )
    evidence = EvidencePack(
        finding_id="vuln_04",
        primary_file="sample.py",
        snippets=[
            CodeSnippet(
                file="sample.py",
                start_line=37,
                end_line=39,
                purpose="is_online_username() with os.system f-string injection",
                text=(
                    "def is_online_username(username):\n"
                    " import os\n"
                    ' os.system(f"touch /tmp/{username}")\n'
                ),
            ),
            CodeSnippet(
                file="sample.py",
                start_line=53,
                end_line=56,
                purpose="External call site: is_online_username called with user-controlled input",
                text=(
                    "# Entry point (CLI / API route):\n"
                    'user_input = input("Check username: ")\n'
                    "is_online_username(user_input)  # user input flows to os.system\n"
                ),
            ),
        ],
        entities={"sink": {"name": "os.system", "file": "sample.py", "line": 39}},
        callers=[
            CallerInfo(
                callee="is_online_username",
                caller_file="sample.py",
                caller_range={"start_line": 53, "end_line": 56},
                notes=(
                    "is_online_username() is called with user-controlled input. "
                    "No sanitization before os.system() at line 39."
                ),
            )
        ],
        dataflow_hypotheses=[
            DataflowHypothesis(
                **{
                    "from": "input() → user_input (caller at line 54)",
                    "to": 'os.system(f"touch /tmp/{username}") at line 39',
                    "path_summary": (
                        "input() → is_online_username(user_input)"
                        " → os.system f-string (no sanitization, clear injection)"
                    ),
                    "confidence": 0.90,
                }
            )
        ],
    )
    trace = TraceResult(
        paths=[
            PathStep(
                file="sample.py",
                function="demo",
                start_line=44,
                end_line=44,
                code_excerpt='username = input("Username: ")',
            ),
            PathStep(
                file="sample.py",
                function="is_online_username",
                start_line=37,
                end_line=39,
                code_excerpt='os.system(f"touch /tmp/{username}")',
            ),
        ],
        gaps=[],
        confidence=0.92,
    )
    mitigations = MitigationsResult()
    assumptions = AssumptionsResult(
        assumptions=[
            Assumption(
                text="username is not sanitized before passing to os.system().",
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:39"],
            )
        ]
    )
    deps = PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln,
        evidence_pack=evidence,
        trace=trace,
        mitigations=mitigations,
        assumptions=assumptions,
    )
    prompt = (
        f"Finding:\n{_serialize_for_prompt(vuln.model_dump())}\n\n"
        f"Evidence Pack:\n{_serialize_for_prompt(evidence)}\n\n"
        f"Trace:\n{_serialize_for_prompt(trace)}\n\n"
        f"Mitigations:\n{_serialize_for_prompt(mitigations)}\n\n"
        f"Assumptions:\n{_serialize_for_prompt(assumptions)}"
    )
    return deps, prompt


# ---------------------------------------------------------------------------
# Build eval inputs (deps + prompt pairs)
# ---------------------------------------------------------------------------

_deps_01, _prompt_01 = _make_deps_01()
_deps_02, _prompt_02 = _make_deps_02()
_deps_03, _prompt_03 = _make_deps_03()
_deps_04, _prompt_04 = _make_deps_04()

# ---------------------------------------------------------------------------
# Task function: runs A5 and returns "VERDICT: <value>\n\nREASONING: <text>"
# ---------------------------------------------------------------------------


async def _run_verdict(inputs: dict[str, object]) -> str:
    agent = create_verdict_agent()
    deps = inputs["deps"]
    prompt = inputs["prompt"]
    result = await agent.run(prompt, deps=deps)  # type: ignore[arg-type]
    output: VerdictResult = result.output
    return f"VERDICT: {output.verdict.value}\n\nREASONING: {output.reasoning}\n\nCONFIDENCE: {output.confidence}"


# ---------------------------------------------------------------------------
# Dataset with LLM judge evaluators
# ---------------------------------------------------------------------------

verdict_dataset: Dataset[dict[str, object], str, None] = Dataset(
    cases=[
        Case(
            name="vuln_01_sqli_tp",
            inputs={"deps": _deps_01, "prompt": _prompt_01},
            expected_output="TRUE_VULNERABILITY",
        ),
        Case(
            name="vuln_02_sqli_fp",
            inputs={"deps": _deps_02, "prompt": _prompt_02},
            expected_output="FALSE_POSITIVE",
        ),
        Case(
            name="vuln_03_ssrf_fp",
            inputs={"deps": _deps_03, "prompt": _prompt_03},
            expected_output="FALSE_POSITIVE",
        ),
        Case(
            name="vuln_04_cmdi_tp",
            inputs={"deps": _deps_04, "prompt": _prompt_04},
            expected_output="TRUE_VULNERABILITY",
        ),
    ],
    evaluators=[
        LLMJudge(
            rubric=(
                "The verdict in the output (TRUE_VULNERABILITY or FALSE_POSITIVE) matches "
                "the expected_output exactly. "
                "The reasoning section cites specific code evidence such as the function name, "
                "code pattern (e.g. 'f-string', 'parameterized query', 'os.system'), "
                "or an approximate line number. "
                "The reasoning is logically coherent and does not contradict the provided evidence."
            ),
            include_input=True,
            include_expected_output=True,
            model=_JUDGE_MODEL,
        ),
        LLMJudge(
            rubric=(
                "The confidence score is coherent with the evidence strength. "
                "If the verdict is TRUE_VULNERABILITY for a clear f-string SQL injection "
                "or os.system call with user input, confidence should be >= 0.7. "
                "If the verdict is FALSE_POSITIVE for a parameterized query or "
                "hardcoded-host SSRF, confidence should be >= 0.7. "
                "Low confidence (<0.5) for clear-cut cases is a quality failure."
            ),
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


async def test_verdict_eval_quality() -> None:
    """LLM judge eval: A5 verdict quality across all four canonical cases."""
    report = await verdict_dataset.evaluate(_run_verdict, max_concurrency=2)
    report.print(include_reasons=True)

    for case_result in report.cases:
        for assertion_name, assertion in case_result.assertions.items():
            assert assertion.value, (
                f"LLM judge failed for case '{case_result.case_id}' "
                f"evaluator '{assertion_name}': {assertion.reason}"
            )

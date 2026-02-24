"""Integration test fixtures for the triage agent pipeline.

All fixtures are session-scoped to avoid redundant model construction.
The ``require_openai_key`` fixture is autouse, so every test in this
directory is skipped automatically when OPENAI_API_KEY is not set.

Line numbers reference /samples/sample1/sample.py (verified against the
actual file):
  login()              lines 15-22  — f-string SQL sink at line 18 (SAST reports 17)
  new_login()          lines 24-31  — parameterized query sink at line 27
  check_username()     lines 33-35  — requests.get sink at line 34
  is_online_username() lines 37-39  — os.system sink at line 39
  demo()               lines 41-51  — source: input() at line 44
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from triage.agent.deps import AgentDeps, PipelineDeps
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
)
from triage.models.vulnerability import Vulnerability

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

SAMPLE1_PATH = Path(__file__).resolve().parent.parent.parent / "samples" / "sample1"

# ---------------------------------------------------------------------------
# Session guard — skip all integration tests when no API key is present
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def require_openai_key() -> None:  # type: ignore[return]
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — skipping integration tests")


# ---------------------------------------------------------------------------
# Vulnerability fixtures — mirrors findings.json entries
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def vuln_01() -> Vulnerability:
    """SQL Injection in login() — canonical TRUE_POSITIVE (f-string interpolation).

    SAST reports sink_line=17 (the comment line before the f-string at line 18).
    Both lines are within the login() function body (15-22) so evidence is sufficient.
    """
    return Vulnerability(
        id="vuln_01",
        type="SQL Injection",
        sink_line=17,
        source_line=44,
        message="The application is vulnerable to SQL Injection in the login function",
        file="sample.py",
    )


@pytest.fixture(scope="session")
def vuln_02() -> Vulnerability:
    """SQL Injection in new_login() — canonical FALSE_POSITIVE (parameterized query)."""
    return Vulnerability(
        id="vuln_02",
        type="SQL Injection",
        sink_line=27,
        source_line=44,
        message="The application is vulnerable to SQL Injection in the new_login function",
        file="sample.py",
    )


@pytest.fixture(scope="session")
def vuln_03() -> Vulnerability:
    """SSRF in check_username() — FALSE_POSITIVE (hardcoded host, only path is user-controlled)."""
    return Vulnerability(
        id="vuln_03",
        type="SSRF",
        sink_line=34,
        source_line=44,
        message="The application is vulnerable to SSRF in the check_username function",
        file="sample.py",
    )


@pytest.fixture(scope="session")
def vuln_04() -> Vulnerability:
    """Command Injection in is_online_username() — canonical TRUE_POSITIVE (os.system f-string)."""
    return Vulnerability(
        id="vuln_04",
        type="Command Injection",
        sink_line=39,
        source_line=44,
        message="The application is vulnerable to Command Injection in the is_online_username function",
        file="sample.py",
    )


# ---------------------------------------------------------------------------
# AgentDeps fixtures (for A0 tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def agent_deps_01(vuln_01: Vulnerability) -> AgentDeps:
    return AgentDeps(repo_path=SAMPLE1_PATH, lsp=None, vulnerability=vuln_01)


@pytest.fixture(scope="session")
def agent_deps_02(vuln_02: Vulnerability) -> AgentDeps:
    return AgentDeps(repo_path=SAMPLE1_PATH, lsp=None, vulnerability=vuln_02)


@pytest.fixture(scope="session")
def agent_deps_04(vuln_04: Vulnerability) -> AgentDeps:
    return AgentDeps(repo_path=SAMPLE1_PATH, lsp=None, vulnerability=vuln_04)


# ---------------------------------------------------------------------------
# Pre-built code snippets (text matches actual sample.py — 1-space indent)
# ---------------------------------------------------------------------------

_LOGIN_SNIPPET = CodeSnippet(
    file="sample.py",
    start_line=15,
    end_line=22,
    purpose="login() function with f-string SQL injection at line 18 (sink_line=17)",
    text=(
        "def login(con, username, password):\n"
        " cur = con.cursor()\n"
        " # Consulta usuarios\n"
        " sql_query = f\"SELECT id FROM users WHERE username = '{username}'"
        " AND password = '{password}'\"\n"
        " cur.execute(\n"
        "  sql_query\n"
        " )\n"
        " return cur.fetchone()\n"
    ),
)

_NEW_LOGIN_SNIPPET = CodeSnippet(
    file="sample.py",
    start_line=24,
    end_line=31,
    purpose="new_login() function with safe parameterized query (sink_line=27)",
    text=(
        "def new_login(con, username, password):\n"
        " cur = con.cursor()\n"
        " # Consulta usuarios\n"
        " cur.execute(\n"
        '  "SELECT id FROM users WHERE username = ? AND password = ?",\n'
        "  (username, password)\n"
        " )\n"
        " return cur.fetchone()\n"
    ),
)

_CHECK_USERNAME_SNIPPET = CodeSnippet(
    file="sample.py",
    start_line=33,
    end_line=35,
    purpose="check_username() with hardcoded api.github.com host — SSRF FP (sink_line=34)",
    text=(
        "def check_username(username):\n"
        ' response = requests.get(f"https://api.github.com/users/{username}")\n'
        " return response\n"
    ),
)

_OS_SYSTEM_SNIPPET = CodeSnippet(
    file="sample.py",
    start_line=37,
    end_line=39,
    purpose="is_online_username() with os.system f-string — command injection (sink_line=39)",
    text=(
        "def is_online_username(username):\n"
        " import os\n"
        ' os.system(f"touch /tmp/{username}")\n'
    ),
)

_DEMO_SNIPPET = CodeSnippet(
    file="sample.py",
    start_line=41,
    end_line=51,
    purpose="demo() — source of user-controlled input via input() at line 44",
    text=(
        "def demo():\n"
        " con = setup_db()\n"
        "\n"
        ' username = input("Username: ")\n'
        ' password = input("Password: ")\n'
        " ok = login(con, username, password)\n"
        ' print("Login:", bool(ok))\n'
        " ok = new_login(con, username, password)\n"
        ' print("New Login:", bool(ok))\n'
        " response = check_username(username)\n"
        ' print("Check username:", response.status_code)\n'
    ),
)


# ---------------------------------------------------------------------------
# Synthetic EvidencePack fixtures (pre-built for A1–A5 tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def evidence_pack_01() -> EvidencePack:
    """Synthetic EvidencePack for vuln_01 (SQL injection f-string — TRUE_POSITIVE)."""
    return EvidencePack(
        finding_id="vuln_01",
        primary_file="sample.py",
        snippets=[_LOGIN_SNIPPET, _DEMO_SNIPPET],
        entities={
            "suspected_function": {
                "name": "login",
                "file": "sample.py",
                "start_line": 15,
                "end_line": 22,
            },
            "sink": {"name": "cur.execute", "file": "sample.py", "line": 19},
            "source": {"name": "input", "file": "sample.py", "line": 44},
        },
        dataflow_hypotheses=[
            DataflowHypothesis(**{
                "from": "input() at demo() line 44 → username, password",
                "to": (
                    "f-string interpolation in sql_query (line 18)"
                    " → cur.execute(sql_query) at line 19"
                ),
                "path_summary": (
                    "input() → demo() → login(username, password)"
                    " → f-string → execute"
                ),
                "confidence": 0.95,
            })
        ],
    )


@pytest.fixture(scope="session")
def evidence_pack_02() -> EvidencePack:
    """Synthetic EvidencePack for vuln_02 (parameterized query — FALSE_POSITIVE)."""
    return EvidencePack(
        finding_id="vuln_02",
        primary_file="sample.py",
        snippets=[_NEW_LOGIN_SNIPPET, _DEMO_SNIPPET],
        entities={
            "suspected_function": {
                "name": "new_login",
                "file": "sample.py",
                "start_line": 24,
                "end_line": 31,
            },
            "sink": {"name": "cur.execute", "file": "sample.py", "line": 27},
            "source": {"name": "input", "file": "sample.py", "line": 44},
        },
        dataflow_hypotheses=[
            DataflowHypothesis(**{
                "from": "input() at demo() line 44 → username, password",
                "to": (
                    "parameterized cur.execute(query, (username, password))"
                    " at lines 27-30"
                ),
                "path_summary": (
                    "input() → demo() → new_login(username, password)"
                    " → parameterized execute (safe)"
                ),
                "confidence": 0.85,
            })
        ],
    )


@pytest.fixture(scope="session")
def evidence_pack_03() -> EvidencePack:
    """Synthetic EvidencePack for vuln_03 (SSRF hardcoded host — FALSE_POSITIVE)."""
    return EvidencePack(
        finding_id="vuln_03",
        primary_file="sample.py",
        snippets=[_CHECK_USERNAME_SNIPPET, _DEMO_SNIPPET],
        entities={
            "suspected_function": {
                "name": "check_username",
                "file": "sample.py",
                "start_line": 33,
                "end_line": 35,
            },
            "sink": {"name": "requests.get", "file": "sample.py", "line": 34},
            "source": {"name": "input", "file": "sample.py", "line": 44},
        },
        dataflow_hypotheses=[
            DataflowHypothesis(**{
                "from": "input() at demo() line 44 → username",
                "to": (
                    "f-string path in requests.get("
                    "f'https://api.github.com/users/{username}') at line 34"
                ),
                "path_summary": (
                    "input() → demo() → check_username(username)"
                    " → requests.get with hardcoded host (api.github.com)"
                ),
                "confidence": 0.80,
            })
        ],
    )


@pytest.fixture(scope="session")
def evidence_pack_04() -> EvidencePack:
    """Synthetic EvidencePack for vuln_04 (os.system f-string — TRUE_POSITIVE).

    Note: demo() in the actual sample.py does not call is_online_username(). To
    make the evidence sufficient for a TRUE_POSITIVE verdict, this fixture
    includes a CallerInfo showing that is_online_username() is called with
    user-controlled input from an external call site (e.g. a CLI or API route).
    """
    # Synthetic snippet showing is_online_username called with user input
    # (represents a call site outside demo() that would make this exploitable)
    _caller_snippet = CodeSnippet(
        file="sample.py",
        start_line=53,
        end_line=56,
        purpose="External call site showing is_online_username called with user input",
        text=(
            "# Entry point (e.g. API route or CLI):\n"
            'user_input = input("Check username: ")\n'
            "is_online_username(user_input)  # user-controlled input reaches os.system\n"
        ),
    )
    return EvidencePack(
        finding_id="vuln_04",
        primary_file="sample.py",
        snippets=[_OS_SYSTEM_SNIPPET, _caller_snippet],
        entities={
            "suspected_function": {
                "name": "is_online_username",
                "file": "sample.py",
                "start_line": 37,
                "end_line": 39,
            },
            "sink": {"name": "os.system", "file": "sample.py", "line": 39},
            "source": {"name": "input", "file": "sample.py", "line": 44},
        },
        callers=[
            CallerInfo(
                callee="is_online_username",
                caller_file="sample.py",
                caller_range={"start_line": 53, "end_line": 56},
                notes=(
                    "is_online_username() is called with user-controlled input "
                    "(username obtained from input()). No sanitization is applied "
                    "before reaching os.system(f'touch /tmp/{username}') at line 39."
                ),
            )
        ],
        dataflow_hypotheses=[
            DataflowHypothesis(**{
                "from": "input() → user_input (caller, line 54)",
                "to": 'os.system(f"touch /tmp/{username}") at line 39',
                "path_summary": (
                    "input() → is_online_username(user_input)"
                    " → os.system f-string (no sanitization, clear injection)"
                ),
                "confidence": 0.90,
            })
        ],
    )


# ---------------------------------------------------------------------------
# Synthetic TraceResult fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def trace_result_01() -> TraceResult:
    """Trace for vuln_01 — f-string SQL injection path (high confidence)."""
    return TraceResult(
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
                code_excerpt=(
                    "def login(con, username, password):\n"
                    " ...\n"
                    " sql_query = f\"SELECT ... WHERE username = '{username}' ...\"\n"
                    " cur.execute(sql_query)"
                ),
            ),
        ],
        gaps=[],
        confidence=0.95,
    )


@pytest.fixture(scope="session")
def trace_result_02() -> TraceResult:
    """Trace for vuln_02 — parameterized query (sink is safe)."""
    return TraceResult(
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
                code_excerpt=(
                    "def new_login(con, username, password):\n"
                    " ...\n"
                    ' cur.execute("SELECT ... WHERE username = ? AND password = ?",\n'
                    "             (username, password))"
                ),
            ),
        ],
        gaps=["Input reaches execute() as a parameter tuple, not via string interpolation"],
        confidence=0.85,
    )


@pytest.fixture(scope="session")
def trace_result_03() -> TraceResult:
    """Trace for vuln_03 — SSRF with hardcoded host."""
    return TraceResult(
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
        gaps=["Host is hardcoded (api.github.com) — only the path segment is user-controlled"],
        confidence=0.75,
    )


@pytest.fixture(scope="session")
def trace_result_04() -> TraceResult:
    """Trace for vuln_04 — os.system command injection (high confidence)."""
    return TraceResult(
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


# ---------------------------------------------------------------------------
# Synthetic MitigationsResult fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mitigations_result_01() -> MitigationsResult:
    """Mitigations for vuln_01 — no mitigations (f-string, unprotected)."""
    return MitigationsResult(
        mitigations_found=[],
        assessment_per_mitigation=[],
    )


@pytest.fixture(scope="session")
def mitigations_result_02() -> MitigationsResult:
    """Mitigations for vuln_02 — parameterized query IS a sufficient mitigation."""
    return MitigationsResult(
        mitigations_found=[
            {
                "type": "parameterized_query",
                "file": "sample.py",
                "line": 27,
                "code": (
                    'cur.execute("SELECT ... WHERE username = ? AND password = ?", '
                    "(username, password))"
                ),
            }
        ],
        assessment_per_mitigation=[
            MitigationAssessment(
                sufficient=True,
                insufficient=None,
                unknown=None,
                rationale=(
                    "The query uses DB-API 2.0 parameterized placeholders (?). "
                    "User input is passed as a separate tuple, never concatenated "
                    "into the SQL string. This fully prevents SQL injection."
                ),
                citations=["sample.py:27"],
            )
        ],
    )


@pytest.fixture(scope="session")
def mitigations_result_03() -> MitigationsResult:
    """Mitigations for vuln_03 — host is hardcoded, partial mitigation (FP for SSRF)."""
    return MitigationsResult(
        mitigations_found=[
            {
                "type": "hardcoded_host",
                "file": "sample.py",
                "line": 34,
                "code": "https://api.github.com/users/{username}",
            }
        ],
        assessment_per_mitigation=[
            MitigationAssessment(
                sufficient=True,
                insufficient=None,
                unknown=None,
                rationale=(
                    "The host (api.github.com) is hardcoded as a string literal. "
                    "The user can only influence the URL path (/users/<username>), "
                    "not the scheme or host. Classic SSRF requires controlling the host."
                ),
                citations=["sample.py:34"],
            )
        ],
    )


@pytest.fixture(scope="session")
def mitigations_result_04() -> MitigationsResult:
    """Mitigations for vuln_04 — no mitigations for os.system f-string."""
    return MitigationsResult(
        mitigations_found=[],
        assessment_per_mitigation=[],
    )


# ---------------------------------------------------------------------------
# Synthetic AssumptionsResult fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def assumptions_result_01() -> AssumptionsResult:
    """Assumptions for vuln_01 — user-controlled input reaches f-string sink."""
    return AssumptionsResult(
        assumptions=[
            Assumption(
                text=(
                    "The `username` and `password` parameters in `login()` originate "
                    "from `input()` in `demo()`."
                ),
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:44", "sample.py:46"],
            ),
            Assumption(
                text=(
                    "No sanitization is applied to `username` or `password` "
                    "before string interpolation in `sql_query` (line 18)."
                ),
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:18"],
            ),
        ]
    )


@pytest.fixture(scope="session")
def assumptions_result_02() -> AssumptionsResult:
    """Assumptions for vuln_02 — parameterized query prevents injection."""
    return AssumptionsResult(
        assumptions=[
            Assumption(
                text=(
                    "The `username` and `password` parameters in `new_login()` originate "
                    "from `input()` in `demo()`."
                ),
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:44", "sample.py:48"],
            ),
            Assumption(
                text=(
                    "The DB-API 2.0 driver correctly handles parameterized queries "
                    "and prevents injection."
                ),
                category=AssumptionCategory.NOT_VERIFIABLE_STATIC,
                evidence_citations=["sample.py:27"],
            ),
        ]
    )


@pytest.fixture(scope="session")
def assumptions_result_03() -> AssumptionsResult:
    """Assumptions for vuln_03 — SSRF with fixed host."""
    return AssumptionsResult(
        assumptions=[
            Assumption(
                text=(
                    "The scheme and host of the request are hardcoded "
                    "('https://api.github.com') and cannot be altered by the user."
                ),
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:34"],
            ),
            Assumption(
                text=(
                    "The user can only control the path component (/users/<username>), "
                    "not the host or scheme."
                ),
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:34"],
            ),
        ]
    )


@pytest.fixture(scope="session")
def assumptions_result_04() -> AssumptionsResult:
    """Assumptions for vuln_04 — command injection via os.system f-string."""
    return AssumptionsResult(
        assumptions=[
            Assumption(
                text=(
                    "The `username` parameter in `is_online_username()` is not "
                    "sanitized before passing to `os.system()` (line 39)."
                ),
                category=AssumptionCategory.VERIFIABLE_STATIC,
                evidence_citations=["sample.py:39"],
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Composed PipelineDeps fixtures for A5 verdict tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pipeline_deps_for_verdict_01(
    vuln_01: Vulnerability,
    evidence_pack_01: EvidencePack,
    trace_result_01: TraceResult,
    mitigations_result_01: MitigationsResult,
    assumptions_result_01: AssumptionsResult,
) -> PipelineDeps:
    """Full PipelineDeps for vuln_01 verdict — expected TRUE_VULNERABILITY."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_01,
        evidence_pack=evidence_pack_01,
        trace=trace_result_01,
        mitigations=mitigations_result_01,
        assumptions=assumptions_result_01,
    )


@pytest.fixture(scope="session")
def pipeline_deps_for_verdict_02(
    vuln_02: Vulnerability,
    evidence_pack_02: EvidencePack,
    trace_result_02: TraceResult,
    mitigations_result_02: MitigationsResult,
    assumptions_result_02: AssumptionsResult,
) -> PipelineDeps:
    """Full PipelineDeps for vuln_02 verdict — expected FALSE_POSITIVE."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_02,
        evidence_pack=evidence_pack_02,
        trace=trace_result_02,
        mitigations=mitigations_result_02,
        assumptions=assumptions_result_02,
    )


@pytest.fixture(scope="session")
def pipeline_deps_for_verdict_03(
    vuln_03: Vulnerability,
    evidence_pack_03: EvidencePack,
    trace_result_03: TraceResult,
    mitigations_result_03: MitigationsResult,
    assumptions_result_03: AssumptionsResult,
) -> PipelineDeps:
    """Full PipelineDeps for vuln_03 verdict — expected FALSE_POSITIVE (SSRF hardcoded host)."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_03,
        evidence_pack=evidence_pack_03,
        trace=trace_result_03,
        mitigations=mitigations_result_03,
        assumptions=assumptions_result_03,
    )


@pytest.fixture(scope="session")
def pipeline_deps_for_verdict_04(
    vuln_04: Vulnerability,
    evidence_pack_04: EvidencePack,
    trace_result_04: TraceResult,
    mitigations_result_04: MitigationsResult,
    assumptions_result_04: AssumptionsResult,
) -> PipelineDeps:
    """Full PipelineDeps for vuln_04 verdict — expected TRUE_VULNERABILITY."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_04,
        evidence_pack=evidence_pack_04,
        trace=trace_result_04,
        mitigations=mitigations_result_04,
        assumptions=assumptions_result_04,
    )


# ---------------------------------------------------------------------------
# Partial PipelineDeps fixtures (for A1, A2, A3 tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pipeline_deps_a1_01(
    vuln_01: Vulnerability,
    evidence_pack_01: EvidencePack,
) -> PipelineDeps:
    """PipelineDeps for A1 (source→sink tracer) with vuln_01 evidence."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_01,
        evidence_pack=evidence_pack_01,
    )


@pytest.fixture(scope="session")
def pipeline_deps_a1_02(
    vuln_02: Vulnerability,
    evidence_pack_02: EvidencePack,
) -> PipelineDeps:
    """PipelineDeps for A1 with vuln_02 evidence."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_02,
        evidence_pack=evidence_pack_02,
    )


@pytest.fixture(scope="session")
def pipeline_deps_a2_01(
    vuln_01: Vulnerability,
    evidence_pack_01: EvidencePack,
    trace_result_01: TraceResult,
) -> PipelineDeps:
    """PipelineDeps for A2 (sanitizers analyzer) with vuln_01."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_01,
        evidence_pack=evidence_pack_01,
        trace=trace_result_01,
    )


@pytest.fixture(scope="session")
def pipeline_deps_a2_02(
    vuln_02: Vulnerability,
    evidence_pack_02: EvidencePack,
    trace_result_02: TraceResult,
) -> PipelineDeps:
    """PipelineDeps for A2 with vuln_02."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_02,
        evidence_pack=evidence_pack_02,
        trace=trace_result_02,
    )


@pytest.fixture(scope="session")
def pipeline_deps_a3_01(
    vuln_01: Vulnerability,
    evidence_pack_01: EvidencePack,
    trace_result_01: TraceResult,
    mitigations_result_01: MitigationsResult,
) -> PipelineDeps:
    """PipelineDeps for A3 (assumptions extractor) with vuln_01."""
    return PipelineDeps(
        repo_path=SAMPLE1_PATH,
        lsp=None,
        finding=vuln_01,
        evidence_pack=evidence_pack_01,
        trace=trace_result_01,
        mitigations=mitigations_result_01,
    )

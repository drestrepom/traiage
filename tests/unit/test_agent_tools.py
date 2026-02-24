import asyncio
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic_ai import RunContext

from triage.agent.deps import AgentDeps
from triage.agent.tools import (
    LIST_FILES_ENTRY_LIMIT,
    grep,
    list_files,
    read_file,
)
from triage.models import Vulnerability

# list_files uses ripgrep only; skip tests when rg is not installed
requires_rg = pytest.mark.skipif(
    not shutil.which("rg"),
    reason="ripgrep (rg) not installed",
)


def _sample_vulnerability() -> Vulnerability:
    return Vulnerability(
        id="test_01",
        type="SQL Injection",
        sink_line=1,
        source_line=1,
        message="Test",
    )


def _ctx(repo_path: Path, vulnerability: Vulnerability | None = None) -> RunContext[AgentDeps]:
    mock = MagicMock(spec=RunContext)
    mock.deps = AgentDeps(
        repo_path=repo_path,
        vulnerability=vulnerability or _sample_vulnerability(),
        lsp=None,
    )
    return mock


@requires_rg
def test_list_files_empty_dir(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    result = asyncio.run(list_files(ctx, ""))
    assert isinstance(result, str)
    assert ".\n" in result or result.startswith(".")


@requires_rg
def test_list_files_returns_names(tmp_path: Path) -> None:
    (tmp_path / "a.py").touch()
    (tmp_path / "b.txt").touch()
    ctx = _ctx(tmp_path)
    result = asyncio.run(list_files(ctx, ""))
    assert isinstance(result, str)
    assert "a.py" in result
    assert "b.txt" in result


def test_read_file(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("hello", encoding="utf-8")
    ctx = _ctx(tmp_path)
    assert read_file(ctx, "f.txt") == "hello"


def test_read_file_escapes_repo(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        read_file(ctx, "../../etc/passwd")


def test_list_files_escapes_repo_raises(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        asyncio.run(list_files(ctx, "../../etc"))


@requires_rg
def test_list_files_excludes_default_patterns(tmp_path: Path) -> None:
    (tmp_path / "a.py").touch()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / ".git").mkdir()
    ctx = _ctx(tmp_path)
    result = asyncio.run(list_files(ctx, ""))
    assert "__pycache__" not in result
    assert ".git" not in result
    assert "a.py" in result


@requires_rg
def test_list_files_returns_markdown(tmp_path: Path) -> None:
    (tmp_path / "foo").mkdir()
    (tmp_path / "foo" / "x").touch()
    ctx = _ctx(tmp_path)
    result = asyncio.run(list_files(ctx, ""))
    assert isinstance(result, str)
    assert result.count("\n") >= 1
    assert "foo" in result


def test_list_files_on_file_path_raises(tmp_path: Path) -> None:
    """list_files requires a directory; passing a file path raises."""
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    ctx = _ctx(tmp_path)
    result = asyncio.run(list_files(ctx, "f.txt"))
    assert "Not a directory" in result


@requires_rg
def test_list_files_truncation_indicated(tmp_path: Path) -> None:
    for i in range(LIST_FILES_ENTRY_LIMIT + 50):
        (tmp_path / f"f{i}.txt").touch()
    ctx = _ctx(tmp_path)
    result = asyncio.run(list_files(ctx, ""))
    assert "truncado" in result or "límite" in result


@requires_rg
def test_list_files_respects_ignore(tmp_path: Path) -> None:
    (tmp_path / "include.txt").touch()
    (tmp_path / "exclude_me").mkdir()
    (tmp_path / "exclude_me" / "x").touch()
    ctx = _ctx(tmp_path)
    result = asyncio.run(list_files(ctx, "", ignore=["exclude_me"]))
    assert "include.txt" in result
    assert "exclude_me" not in result


# --- grep tool (uses ripgrep) ---


@requires_rg
def test_grep_finds_pattern(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def foo(): pass\nx = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def bar(): pass\n", encoding="utf-8")
    ctx = _ctx(tmp_path)
    result = asyncio.run(grep(ctx, r"def\s+\w+", path=""))
    assert "Found" in result and "matches" in result
    assert "a.py" in result
    assert "b.py" in result
    assert "def foo" in result or "Line 1" in result
    assert "def bar" in result or "Line 1" in result


@requires_rg
def test_grep_no_matches(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("hello world", encoding="utf-8")
    ctx = _ctx(tmp_path)
    result = asyncio.run(grep(ctx, "NOMATCH_PATTERN_XYZ", path=""))
    assert result == "No files found"


def test_grep_empty_pattern_raises(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    with pytest.raises(ValueError, match="pattern is required"):
        asyncio.run(grep(ctx, "  ", path=""))


@requires_rg
def test_grep_path_can_be_file(tmp_path: Path) -> None:
    """When path is a file, grep searches only that file."""
    (tmp_path / "f.txt").write_text("needle in file", encoding="utf-8")
    (tmp_path / "other.txt").write_text("needle here too", encoding="utf-8")
    ctx = _ctx(tmp_path)
    result = asyncio.run(grep(ctx, "needle", path="f.txt"))
    assert "f.txt" in result
    assert "other.txt" not in result


@requires_rg
def test_grep_include_glob(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("needle", encoding="utf-8")
    (tmp_path / "b.txt").write_text("needle", encoding="utf-8")
    ctx = _ctx(tmp_path)
    result = asyncio.run(grep(ctx, "needle", path="", include="*.py"))
    assert "a.py" in result
    assert "b.txt" not in result

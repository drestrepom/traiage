"""Unit tests for LSP tools (multilspy-backed)."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic_ai import RunContext

from triage.agent.deps import AgentDeps, BaseDeps
from triage.agent.tools.lsp import (
    lsp_document_symbol,
    lsp_go_to_definition,
    start_lsp_client,
)
from triage.models import Vulnerability

SAMPLE1_PATH = Path(__file__).resolve().parent.parent.parent / "samples" / "sample1"


def _sample_vulnerability() -> Vulnerability:
    return Vulnerability(
        id="test_01",
        type="SQL Injection",
        sink_line=1,
        source_line=1,
        message="Test",
    )


def _ctx(repo_path: Path, lsp: Any = None) -> RunContext[BaseDeps]:
    mock = MagicMock(spec=RunContext)
    mock.deps = AgentDeps(
        repo_path=repo_path,
        vulnerability=_sample_vulnerability(),
        lsp=lsp,
    )
    return mock


@pytest.mark.asyncio
async def test_lsp_go_to_definition_escapes_repo_raises(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        await lsp_go_to_definition(ctx, "../../etc/passwd", line=1, symbol_name="x")


@pytest.mark.asyncio
async def test_lsp_go_to_definition_file_not_found_raises(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    with pytest.raises(FileNotFoundError, match="Not a file or not found"):
        await lsp_go_to_definition(ctx, "nonexistent.py", line=1, symbol_name="x")


@pytest.mark.asyncio
async def test_lsp_document_symbol_escapes_repo_raises(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        await lsp_document_symbol(ctx, "../../etc/passwd")


@pytest.mark.asyncio
async def test_lsp_requires_initialized_lsp(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    ctx = _ctx(tmp_path, lsp=None)
    result = await lsp_go_to_definition(ctx, "a.py", line=1, symbol_name="x")
    assert "LSP unavailable" in result
    assert "LSP not initialized" in result


@pytest.mark.asyncio
async def test_lsp_go_to_definition_accepts_absolute_and_returns_relative() -> None:
    """Open/close LSP in same task to avoid anyio 'exit cancel scope in different task'."""
    async with start_lsp_client(SAMPLE1_PATH) as lsp:
        ctx = _ctx(SAMPLE1_PATH, lsp=lsp)
        result = await lsp_go_to_definition(
            ctx, "sample.py", line=46, symbol_name="login"
        )

    assert "Definiciones encontradas" in result
    assert "file://" not in result
    assert str(SAMPLE1_PATH) not in result
    assert "sample.py" in result


@pytest.mark.asyncio
async def test_lsp_document_symbol_marks_relative_path() -> None:
    """Open/close LSP in same task to avoid anyio 'exit cancel scope in different task'."""
    async with start_lsp_client(SAMPLE1_PATH) as lsp:
        ctx = _ctx(SAMPLE1_PATH, lsp=lsp)
        result = await lsp_document_symbol(ctx, "sample.py")

    assert "Symbols in `sample.py`" in result
    assert "file://" not in result
    assert str(SAMPLE1_PATH) not in result
    assert "setup_db" in result
    assert "login" in result
    assert "demo" in result


@pytest.mark.skip(reason="lsp_workspace_symbol tool not implemented")
@pytest.mark.asyncio
async def test_lsp_workspace_symbol_uses_relative_paths() -> None:
    """Tool runs without leaking absolute paths; if server returns symbols, they use relative paths."""
    ...


@pytest.mark.skip(reason="lsp_workspace_symbol tool not implemented")
@pytest.mark.asyncio
async def test_lsp_workspace_symbol_no_results_when_request_returns_empty() -> None:
    """When query matches no symbols, tool returns no-results message."""
    ...

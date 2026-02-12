from typing import Annotated

from pydantic import Field
from pydantic_ai import RunContext, Tool

from triage.agent.deps import BaseDeps
from triage.agent.tools.common import resolve_repo_path


def read_file_lines(
    ctx: RunContext[BaseDeps],
    relative_path: Annotated[
        str,
        Field(description="Path to the file relative to the repository root."),
    ],
    start_line: Annotated[
        int,
        Field(description="First line to read (1-based, inclusive)."),
    ],
    end_line: Annotated[
        int,
        Field(description="Last line to read (1-based, inclusive)."),
    ],
) -> str:
    """Read lines [start_line, end_line] from a file in the repo. Line numbers are 1-based."""
    if not relative_path or not relative_path.strip():
        raise ValueError("relative_path is required")
    if start_line < 1 or end_line < 1:
        raise ValueError("start_line and end_line must be >= 1")
    if start_line > end_line:
        raise ValueError("start_line must be <= end_line")
    target = resolve_repo_path(ctx, relative_path)
    if not target.is_file():
        return f"File not found: {relative_path}"
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines:
        return f"File is empty: {relative_path}"
    # 1-based to 0-based; end_line inclusive
    lo = max(0, start_line - 1)
    hi = min(len(lines), end_line)
    if lo >= len(lines):
        return f"Line {start_line} is out of range (file has {len(lines)} lines): {relative_path}"
    selected = lines[lo:hi]
    return "\n".join(selected)


READ_FILE_LINES_TOOL = Tool(
    read_file_lines,
    name="read_file_lines",
    description="Read a range of lines from a file in the repository. Use this to embed real code when the report section references file:line or file:start-end. Line numbers are 1-based and inclusive.",
    takes_ctx=True,
)

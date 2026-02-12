from typing import Annotated
from pydantic import Field
from pydantic_ai import RunContext, Tool

from triage.agent.deps import BaseDeps
from triage.agent.tools.common import resolve_repo_path

LINES_LIMIT = 100


def read_file(
    ctx: RunContext[BaseDeps],
    relative_path: Annotated[
        str | None,
        Field(description="The path to the file to read from the repository root."),
    ] = None,
    offset: Annotated[
        int, Field(description="The number of lines to offset the file from the start.")
    ] = 0,
) -> str:
    if relative_path is None or not relative_path.strip():
        raise ValueError("relative_path is required")
    target = resolve_repo_path(ctx, relative_path)
    if not target.is_file():
        raise FileNotFoundError(f"Not a file or not found: {relative_path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > LINES_LIMIT + offset:
        return (
            "\n".join(lines[offset : LINES_LIMIT + offset])
            + "\n...\n"
            + "File truncated"
        )
    return "\n".join(lines[offset:])


READ_FILE_TOOL = Tool(
    read_file,
    name="read_file",
    description="Return the contents of a file at a path relative to the repository root.",
    takes_ctx=True,
)

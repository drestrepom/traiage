from typing import Annotated
from lsp_client import Position
from pydantic import Field
from pydantic_ai import RunContext, Tool

from triage.agent.deps import BaseDeps
from triage.agent.tools.lsp.common import (
    abs_path,
    format_locations_markdown,
    get_lsp,
    preferred_character_for_line,
)


async def lsp_find_references(
    ctx: RunContext[BaseDeps],
    file_path: str,
    line: Annotated[int, Field(description="1-based line number")],
) -> str:
    abs_path_obj = abs_path(ctx, file_path)
    norm_line = max(line, 1)
    char0 = preferred_character_for_line(abs_path_obj, norm_line)
    lsp = get_lsp(ctx)
    try:
        result = await lsp.request_references(
            file_path=abs_path_obj,
            position=Position(line=norm_line - 1, character=char0),
        )
    except Exception as e:
        return f"Error finding references: {e}"
    return format_locations_markdown(
        ctx,
        result,
        header="References found",
        empty_operation_name="find_references",
    )


LSP_FIND_REFERENCES_TOOL = Tool(
    lsp_find_references,
    name="lsp_find_references",
    description=(
        "Find all references to the symbol at the given file position. "
        "line and character are 1-based (as in editors)."
    ),
    takes_ctx=True,
    max_retries=3,
)

from typing import Annotated
from pydantic import Field
from lsp_client import Position
from pydantic_ai import RunContext, Tool

from triage.agent.deps import AgentDeps
from triage.agent.tools.lsp.common import (
    abs_path,
    get_lsp,
    preferred_character_for_line,
)


async def lsp_hover(
    ctx: RunContext[AgentDeps],
    file_path: str,
    line: Annotated[int, Field(description="1-based line number")],
) -> str:
    abs_path_obj = abs_path(ctx, file_path)
    _0_based_line = line - 1
    ts_char0 = preferred_character_for_line(abs_path_obj, line)
    lsp = get_lsp(ctx)

    result = await lsp.request_hover(
        file_path=abs_path_obj,
        position=Position(line=_0_based_line, character=ts_char0),
    )
    if not result:
        return "No results found for hover"

    value = result.value
    if not value:
        return "No results found for hover"

    return f"**Hover:**\n\n{value}"


LSP_HOVER_TOOL = Tool(
    lsp_hover,
    name="lsp_hover",
    description=(
        "Get hover (e.g. type/signature) information at the given file position. "
        "line and character are 1-based (as in editors)."
    ),
    takes_ctx=True,
)

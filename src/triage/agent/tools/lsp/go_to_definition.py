from pathlib import Path
from typing import Annotated, Sequence

from lsp_client import Position
from pydantic import Field
from pydantic_ai import RunContext, Tool

from triage.agent.deps import BaseDeps
from triage.agent.tools.lsp.common import (
    abs_path,
    format_locations_markdown,
    get_lsp,
)
from triage.utils.tree import (
    find_largest_node_for_line,
    find_smallest_node_containing_text_in_line,
)


async def lsp_go_to_definition(
    ctx: RunContext[BaseDeps],
    file_path: str,
    line: Annotated[int, Field(description="1-based line number")],
    symbol_name: Annotated[
        str,
        Field(
            description="The name of the symbol to find the definition of, case sensitive"
        ),
    ],
) -> str:
    abs_path_obj: Path = abs_path(ctx, file_path)
    _0_based_line = line - 1
    node = find_smallest_node_containing_text_in_line(abs_path_obj, line, symbol_name)
    if node is None:
        return "No results found for go_to_definition"
    char0 = node.start_point.column
    lsp = get_lsp(ctx)

    output_lines: list[str] = []
    results = await lsp.request_definition(
        file_path=abs_path_obj,
        position=Position(line=_0_based_line, character=char0),
    )
    if not results:
        return "No results found for go_to_definition"
    for result in results if isinstance(results, Sequence) else [results]:
        node = find_largest_node_for_line(abs_path_obj, result.range.start.line + 1)
        output_lines.append(
            format_locations_markdown(
                ctx,
                result,
                header="Definiciones encontradas",
                empty_operation_name="go_to_definition",
            )
        )
        if node is not None:
            node_snippet = node.text.decode("utf-8", errors="replace")
            output_lines.append("**Origin node (tree-sitter):**\n\n")
            output_lines.append(f"```python\n{node_snippet}\n```\n\n")

    return "\n".join(output_lines)


LSP_GO_TO_DEFINITION_TOOL = Tool(
    lsp_go_to_definition,
    name="lsp_go_to_definition",
    description=(
        "Find the definition of the symbol at the given file position. "
        "line and character are 1-based (as in editors)."
    ),
    takes_ctx=True,
    max_retries=3,
)

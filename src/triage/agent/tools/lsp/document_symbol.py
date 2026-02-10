from typing import Sequence

from pydantic_ai import RunContext, Tool

from triage.agent.deps import AgentDeps
from triage.agent.tools.lsp import SYMBOL_KIND_NAMES
from triage.agent.tools.lsp.common import (
    abs_path,
    get_lsp,
    relative_to_repo,
)
from lsp_client.utils.types import lsp_type


def format_document_symbols_markdown(
    ctx: RunContext[AgentDeps],
    symbols: Sequence[lsp_type.SymbolInformation]
    | Sequence[lsp_type.DocumentSymbol]
    | None,
    file_path: str,
) -> str:
    if not symbols:
        return "No results found for document_symbol"

    rel_path = relative_to_repo(ctx, file_path)
    lines: list[str] = [f"**Symbols in `{rel_path}`:**"]

    for sym in symbols or []:
        # Convert to 1-based
        start_line = sym.range.start.line + 1
        end_line = sym.range.end.line + 1

        kind_value = sym.kind
        kind_name = (
            SYMBOL_KIND_NAMES.get(kind_value.value)
            if isinstance(kind_value, lsp_type.SymbolKind)
            else None
        )
        kind_str = f" ({kind_name})" if kind_name else ""

        if start_line is not None and end_line is not None and end_line != start_line:
            pos_str = f" - lines {start_line}-{end_line}"
        elif start_line is not None:
            pos_str = f" - line {start_line}"
        else:
            pos_str = ""

        lines.append(f"- `{sym.name}`{kind_str}{pos_str}")

    if len(lines) == 1:
        return "No results found for document_symbol"

    return "\n".join(lines)


async def lsp_document_symbol(ctx: RunContext[AgentDeps], file_path: str) -> str:
    abs_path_obj = abs_path(ctx, file_path)
    lsp = get_lsp(ctx)

    result = await lsp.request_document_symbol(file_path=abs_path_obj)

    return format_document_symbols_markdown(ctx, result, str(abs_path_obj))


LSP_DOCUMENT_SYMBOL_TOOL = Tool(
    lsp_document_symbol,
    name="lsp_document_symbol",
    description="List all document symbols (e.g. classes, functions) in the file.",
    takes_ctx=True,
)

from pydantic_ai import RunContext, Tool

from triage.agent.deps import AgentDeps
from triage.agent.tools.lsp import SYMBOL_KIND_NAMES
from triage.agent.tools.lsp.common import (
    get_lsp,
    relative_to_repo,
)
from lsp_client.utils.types import lsp_type


def format_workspace_symbols_markdown(
    ctx: RunContext[AgentDeps],
    symbols: list[lsp_type.SymbolInformation] | list[lsp_type.WorkspaceSymbol],
) -> str:
    if not symbols:
        return "No results found for workspace_symbol"

    lines: list[str] = ["**Símbolos en el workspace:**"]

    for sym in symbols:
        name = sym.name
        kind = sym.kind
        location = sym.location

        uri = location.uri
        range_ = location.range
        # Convertir a 1-based
        start_line = range_.start.line + 1
        end_line = range_.end.line + 1

        rel_path = relative_to_repo(ctx, str(uri))

        kind_name = SYMBOL_KIND_NAMES.get(kind.value) if kind else None
        kind_str = f" ({kind_name})" if kind_name else ""

        if start_line is not None and end_line is not None and end_line != start_line:
            pos_str = f" - líneas {start_line}-{end_line}"
        elif start_line is not None:
            pos_str = f" - línea {start_line}"
        else:
            pos_str = ""

        lines.append(f"- `{name}` en `{rel_path}`{kind_str}{pos_str}")

    if len(lines) == 1:
        return "No results found for workspace_symbol"

    return "\n".join(lines)


async def lsp_workspace_symbol(ctx: RunContext[AgentDeps], query: str = "") -> str:
    lsp = get_lsp(ctx)

    result = await lsp.request_workspace_symbol(query=query)
    return format_workspace_symbols_markdown(ctx, result)


LSP_WORKSPACE_SYMBOL_TOOL = Tool(
    lsp_workspace_symbol,
    name="lsp_workspace_symbol",
    description="Search for symbols in the workspace matching the query.",
    takes_ctx=True,
)

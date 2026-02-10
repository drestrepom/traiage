import logging
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import unquote, urlparse
from lsp_client import lsp_type
from lsp_client.clients.pyright import PyrightClient
from pydantic_ai import RunContext

from triage.agent.deps import AgentDeps
from triage.agent.tools.common import resolve_repo_path
from triage.agent.tools.utils.tree import (
    find_largest_node_for_line,
)

logger = logging.getLogger(__name__)

# LSP SymbolKind mapping (from LSP spec)
SYMBOL_KIND_NAMES: dict[int, str] = {
    1: "File",
    2: "Module",
    3: "Namespace",
    4: "Package",
    5: "Class",
    6: "Method",
    7: "Property",
    8: "Field",
    9: "Constructor",
    10: "Enum",
    11: "Interface",
    12: "Function",
    13: "Variable",
    14: "Constant",
    15: "String",
    16: "Number",
    17: "Boolean",
    18: "Array",
    19: "Object",
    20: "Key",
    21: "Null",
    22: "EnumMember",
    23: "Struct",
    24: "Event",
    25: "Operator",
    26: "TypeParameter",
}


def start_lsp_client(workspace: Path) -> PyrightClient:
    return PyrightClient(workspace=workspace)


def get_lsp(ctx: RunContext[AgentDeps]) -> PyrightClient:
    lsp = getattr(ctx.deps, "lsp", None)
    if lsp is None:
        raise RuntimeError(
            "LSP not initialized; start a session with start_lsp_client and pass lsp in deps.",
        )
    return lsp


def abs_path(ctx: RunContext[AgentDeps], file_path: str) -> Path:
    path_obj = Path(file_path)
    if path_obj.is_absolute():
        repo_root = ctx.deps.repo_path.resolve()
        resolved = path_obj.resolve()
        try:
            _ = resolved.relative_to(repo_root)
        except ValueError:
            raise ValueError(f"Path escapes repository: {file_path}")
    else:
        resolved = resolve_repo_path(ctx, file_path)

    if not resolved.is_file():
        raise FileNotFoundError(f"Not a file or not found: {file_path}")

    return resolved


def preferred_character_for_line(abs_path: Path, one_based_line: int) -> int:
    ts_node = find_largest_node_for_line(abs_path, one_based_line)
    if not ts_node:
        return 0
    for named_child in ts_node.named_children:
        return named_child.start_point.column
    return 0


def repo_root(ctx: RunContext[AgentDeps]) -> Path:
    return ctx.deps.repo_path.resolve()


def relative_to_repo(ctx: RunContext[AgentDeps], file_uri_or_path: str) -> str:
    root = repo_root(ctx)

    if file_uri_or_path.startswith("file://"):
        parsed = urlparse(file_uri_or_path)
        path = Path(unquote(parsed.path))
    else:
        path = Path(file_uri_or_path)

    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _get_attr_or_key(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def format_locations_markdown(
    ctx: RunContext[AgentDeps],
    locations: lsp_type.Location
    | Sequence[lsp_type.Location]
    | Sequence[lsp_type.LocationLink]
    | None,
    header: str,
    empty_operation_name: str,
) -> str:
    if not locations:
        return f"No results found for {empty_operation_name}"

    lines: list[str] = [f"**{header}:**"]

    for loc in locations if isinstance(locations, Sequence) else [locations]:
        uri = loc.uri if isinstance(loc, lsp_type.Location) else loc.target_uri
        range_ = (
            loc.range
            if isinstance(loc, lsp_type.Location)
            else loc.target_selection_range
        )

        if uri is None:
            continue

        start = range_.start
        line = start.line
        character = _get_attr_or_key(start, "character") if start else None

        if line is not None:
            line = line + 1
        if character is not None:
            character = character + 1

        rel_path = relative_to_repo(ctx, str(uri))
        line_str = "?" if line is None else str(line)
        char_str = "?" if character is None else str(character)

        lines.append(f"- `{rel_path}:{line_str}:{char_str}`")

    if len(lines) == 1:
        return f"No results found for {empty_operation_name}"

    return "\n".join(lines)


def format_hover_markdown(
    ctx: RunContext[AgentDeps],
    result: Any,
) -> str:
    if result is None:
        return "No results found for hover"

    contents = getattr(result, "contents", None)
    if contents is None:
        return "No results found for hover"

    value = getattr(contents, "value", None)
    if value:
        return f"**Hover:**\n\n{value}"

    content_str = str(contents)
    if content_str:
        return f"**Hover:**\n\n{content_str}"

    return "No results found for hover"

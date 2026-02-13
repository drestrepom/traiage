from typing import Annotated

from pydantic import Field
from pydantic_ai import RunContext, Tool

from triage.agent.deps import BaseDeps
from triage.agent.tools.common import resolve_repo_path
from triage.utils.tree import enumerate_nodes_in_line, find_function_node_for_line


def get_function_code(
    ctx: RunContext[BaseDeps],
    relative_path: Annotated[
        str,
        Field(description="Path to the file relative to the repository root."),
    ],
    line_number: Annotated[
        int,
        Field(description="1-based line number inside the target function."),
    ],
) -> str:
    """Return the full source code of the function that contains the given line."""
    if not relative_path or not relative_path.strip():
        raise ValueError("relative_path is required")
    if line_number < 1:
        raise ValueError("line_number must be >= 1")
    target = resolve_repo_path(ctx, relative_path)
    if not target.is_file():
        return f"File not found: {relative_path}"
    node = find_function_node_for_line(target, line_number)
    if node is None:
        return f"No function found at line {line_number} in {relative_path}\n{enumerate_nodes_in_line(node)}"
    return enumerate_nodes_in_line(node)


GET_FUNCTION_CODE_TOOL = Tool(
    get_function_code,
    name="get_function_code",
    description=(
        "Return the complete source code of the Python function that contains a given line. "
        "Provide the file path relative to the repository root and any 1-based line number "
        "that falls inside the function body."
    ),
    takes_ctx=True,
)

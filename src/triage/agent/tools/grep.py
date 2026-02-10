import asyncio
import shutil
from pathlib import Path
from typing import NamedTuple

from pydantic_ai import RunContext, Tool

from triage.agent.deps import AgentDeps
from triage.agent.tools._common import resolve_repo_path

MAX_LINE_LENGTH = 2000
GREP_MATCH_LIMIT = 100


class _Match(NamedTuple):
    path: str
    mod_time: float
    line_num: int
    line_text: str


async def _run_ripgrep(
    search_path: Path,
    pattern: str,
    include: str | None,
) -> list[_Match]:
    if not shutil.which("rg"):
        raise FileNotFoundError("ripgrep (rg) is required but not found in PATH")

    args = [
        "rg",
        "-nH",
        "--hidden",
        "--no-messages",
        "--field-match-separator=|",
        "--regexp",
        pattern,
    ]
    if include:
        args.extend(["--glob", include])
    args.append(str(search_path))

    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=search_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    returncode = proc.returncode

    # Exit codes: 0 = matches, 1 = no matches, 2 = errors (e.g. broken symlinks)
    if returncode == 1 or (returncode == 2 and not (stdout or b"").strip()):
        return []

    if returncode not in (0, 2):
        err = (stderr or b"").decode(errors="replace")
        raise RuntimeError(f"ripgrep failed: {err}")

    lines = (stdout or b"").decode(errors="replace").strip().splitlines()
    matches: list[_Match] = []

    for line in lines:
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        file_path, line_num_str, line_text = parts
        if not file_path or not line_num_str:
            continue
        try:
            line_num = int(line_num_str, 10)
        except ValueError:
            continue
        try:
            stat = Path(file_path).stat()
            mod_time = stat.st_mtime
        except OSError:
            continue
        matches.append(
            _Match(
                path=file_path,
                mod_time=mod_time,
                line_num=line_num,
                line_text=line_text,
            )
        )

    matches.sort(key=lambda m: m.mod_time, reverse=True)
    return matches


async def grep(
    ctx: RunContext[AgentDeps],
    pattern: str,
    path: str | None = None,
    include: str | None = None,
) -> str:
    if not pattern.strip():
        raise ValueError("pattern is required")

    resolved = resolve_repo_path(ctx, path or ".")
    if resolved.is_file():
        search_path = resolved.parent
        effective_include = resolved.name
    elif resolved.is_dir():
        search_path = resolved
        effective_include = include
    else:
        raise ValueError(f"Path does not exist: {path or '.'}")

    matches = await _run_ripgrep(search_path, pattern, effective_include)

    if not matches:
        return "No files found"

    truncated = len(matches) > GREP_MATCH_LIMIT
    final = matches[:GREP_MATCH_LIMIT]

    lines_out: list[str] = [f"Found {len(final)} matches"]
    current_file = ""
    for m in final:
        if m.path != current_file:
            if current_file:
                lines_out.append("")
            current_file = m.path
            lines_out.append(f"{m.path}:")
        text = m.line_text
        if len(text) > MAX_LINE_LENGTH:
            text = text[:MAX_LINE_LENGTH] + "..."
        lines_out.append(f"  Line {m.line_num}: {text}")

    if truncated:
        lines_out.append("")
        lines_out.append(
            "(Results are truncated. Consider using a more specific path or pattern.)"
        )

    return "\n".join(lines_out)


GREP_TOOL = Tool(
    grep,
    name="grep",
    description=(
        "Fast content search using regex in file contents. "
        "Searches with full regex syntax (e.g. 'log.*Error', 'function\\s+\\w+'). "
        "Use the include parameter to filter by file pattern (e.g. '*.js', '*.{ts,tsx}'). "
        "Returns file paths and line numbers with matches, sorted by modification time. "
        "Use when you need to find files containing specific patterns. "
        "For counting matches or complex searches, use the Bash tool with 'rg' directly; do not use grep. "
        "For open-ended exploration, use the list_files tool instead."
    ),
    takes_ctx=True,
)

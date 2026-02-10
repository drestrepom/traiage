import shutil
from pathlib import Path
import asyncio
from typing import Annotated
from pydantic import Field
from pydantic_ai import RunContext, Tool

from triage.agent.deps import AgentDeps
from triage.agent.tools.common import resolve_repo_path

DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    "node_modules/",
    "__pycache__/",
    ".git/",
    "dist/",
    "build/",
    "target/",
    "vendor/",
    "bin/",
    "obj/",
    ".idea/",
    ".vscode/",
    ".zig-cache/",
    "zig-out",
    ".coverage",
    "coverage/",
    "tmp/",
    "temp/",
    ".cache/",
    "cache/",
    "logs/",
    ".venv/",
    "venv/",
    "env/",
    ".tox/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".pytest_cache/",
    "*.pyc",
)

LIST_FILES_ENTRY_LIMIT: int = 100


def _ignore_to_ripgrep_glob(pattern: str) -> str:
    p = pattern.rstrip("/")
    if p.startswith("*"):
        return f"!{p}"
    return f"!{p}*"


async def _list_files_ripgrep(
    search_path: Path, ignore_globs: list[str], limit: int
) -> list[str]:
    if not shutil.which("rg"):
        raise FileNotFoundError("ripgrep (rg) is required but not found in PATH")
    args = ["rg", "--files", "--sort=path"]
    for g in ignore_globs:
        args.extend(["-g", g])
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=search_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    returncode = await proc.wait()
    stdout, stderr = await proc.communicate()
    if returncode != 0 and stderr and "No such file" in stderr.decode():
        raise FileNotFoundError(str(search_path))
    lines = (stdout.decode() or "").strip().splitlines()
    return lines[:limit]


def _parent_dir(path_str: str) -> str:
    if path_str == "." or "/" not in path_str:
        return "."
    return path_str.rsplit("/", 1)[0]


def _build_tree(files: list[str]) -> tuple[set[str], dict[str, list[str]]]:
    dirs: set[str] = set()
    files_by_dir: dict[str, list[str]] = {}
    for file_path in files:
        p = Path(file_path)
        dir_part = "." if len(p.parts) <= 1 else p.parent.as_posix()
        parts = dir_part.split("/") if dir_part != "." else []
        for i in range(len(parts) + 1):
            d = "." if i == 0 else "/".join(parts[:i])
            dirs.add(d)
        if dir_part not in files_by_dir:
            files_by_dir[dir_part] = []
        files_by_dir[dir_part].append(p.name)
    return dirs, files_by_dir


def _render_dir(
    dir_path: str,
    depth: int,
    dirs: set[str],
    files_by_dir: dict[str, list[str]],
) -> str:
    indent = "  " * depth
    out: list[str] = []
    if depth > 0:
        out.append(f"{indent}{Path(dir_path).name}/")
    child_indent = "  " * (depth + 1)
    children = sorted(d for d in dirs if _parent_dir(d) == dir_path and d != dir_path)
    for child in children:
        out.append(_render_dir(child, depth + 1, dirs, files_by_dir))
    for f in sorted(files_by_dir.get(dir_path, [])):
        out.append(f"{child_indent}{f}")
    return "\n".join(out)


async def list_files(
    ctx: RunContext[AgentDeps],
    relative_path: Annotated[
        str,
        Field(
            description="The path to the directory to list from the repository root."
        ),
    ] = "",
    ignore: list[str] | None = None,
) -> str:
    target = resolve_repo_path(ctx, relative_path or ".")
    if not target.is_dir():
        return f"Not a directory: {relative_path or '.'}"

    ignore_globs = [_ignore_to_ripgrep_glob(p) for p in DEFAULT_IGNORE_PATTERNS]
    if ignore:
        ignore_globs.extend(_ignore_to_ripgrep_glob(p) for p in ignore)

    files = await _list_files_ripgrep(target, ignore_globs, LIST_FILES_ENTRY_LIMIT)
    truncated = len(files) >= LIST_FILES_ENTRY_LIMIT

    dirs, files_by_dir = _build_tree(files)
    display_path = target.as_posix()
    try:
        rel = target.relative_to(ctx.deps.repo_path.resolve())
        display_path = rel.as_posix() if rel.parts else "."
    except ValueError:
        pass

    body = _render_dir(".", 0, dirs, files_by_dir)
    output = f"{display_path}/\n{body}"
    if truncated:
        output += f"\n\n*… (truncado, límite {LIST_FILES_ENTRY_LIMIT} entradas)*"
    return output


LIST_FILES_TOOL = Tool(
    list_files,
    name="list_files",
    description=(
        "List files and directories in a given path using ripgrep. "
        "The path parameter is relative to the repository root; omit it to use the repo root. "
        "You can optionally provide an array of glob patterns to ignore with the ignore parameter. "
        "Prefer Glob and Grep tools when you know which directories to search."
    ),
    takes_ctx=True,
)

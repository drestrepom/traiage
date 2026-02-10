from pathlib import Path

from pydantic_ai import RunContext

from triage.agent.deps import AgentDeps


def resolve_repo_path(ctx: RunContext[AgentDeps], relative_path: str) -> Path:
    base = ctx.deps.repo_path.resolve()
    resolved = (base / relative_path).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f"Path escapes repository: {relative_path}")
    return resolved

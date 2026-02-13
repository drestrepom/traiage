import asyncio
import logging
from pathlib import Path

import logfire

from triage.agent.agents.report_formatter import create_report_formatter_agent
from triage.agent.deps import BaseDeps
from triage.agent.orchestrator import _serialize_for_prompt
from triage.models.pipeline import PipelineReport, TriagePipelineReport
from triage.report.markdown_report import (
    _render_single_report,
    render_pipeline_report_markdown,
)

logger = logging.getLogger(__name__)

FINDING_REPORT_TEMPLATE = """\
## Finding: {finding.id} ({finding.type})

Verdict: **{verdict}** [— Severity: {severity}] [— Priority: {priority}] — Confidence: {confidence}

{verdict_reasoning}

> **Severity rationale:** {severity_rationale}
> **Suggested fix:** `{suggested_fix}`

### Trace (Source → Sink)
1. `{file}:{function}` L{start}–{end}: `{code_excerpt_first_line}`
2. `{file}:{function}` L{start}–{end}: `{code_excerpt_first_line}`
*(repeat one numbered item per PathStep from source_to_sink_trace.paths; omit this note in output)*
- Gaps: {gaps}

### Sanitizers on path
- {Sufficient|Insufficient|Unknown}: {rationale}

### Evidence
- Source (`{file}` L{start}–{end}):
  ```python
  {code}
  ```
- Sink (`{file}` L{start}–{end}):
  ```python
  {code}
  ```

### Assumptions
- {assumption_text} *(category A = statically verifiable; B = requires deployment context)*

### Counterexample *(only when verdict is FALSE_POSITIVE)*
- **Type:** {type}
- {explanation}
- **FP Mechanism:** {fp_mechanism}

### See also
[OWASP AXX:2025 – Category](url)
"""


async def _enrich_finding(
    r: TriagePipelineReport,
    repo_path: Path,
    model: str,
) -> str:
    agent = create_report_formatter_agent(model=model)
    deps = BaseDeps(repo_path=repo_path.resolve(), lsp=None)
    serialized = _serialize_for_prompt(r.model_dump())
    user_prompt = (
        f"Fill in the following template for one security finding report.\n\n"
        f"## Template\n\n{FINDING_REPORT_TEMPLATE}\n\n"
        f"## Report Data\n\n{serialized}"
    )
    try:
        with logfire.span("enrich_finding", finding_id=r.finding.id):
            result = await agent.run(user_prompt, deps=deps)
        return result.output.content
    except Exception as e:
        logger.warning("Report formatter failed for finding %s: %s", r.finding.id, e)
        return "\n".join(_render_single_report(r))


async def generate_enriched_reports(
    pipeline_report: PipelineReport,
    repo_path: Path,
    model: str = "openai:gpt-5-mini",
    use_agent: bool = True,
) -> str:
    repo_path = repo_path.resolve()
    if not use_agent:
        return render_pipeline_report_markdown(pipeline_report)

    lines: list[str] = ["# Pipeline report", ""]
    if not pipeline_report.reports:
        lines.extend(["There are no findings in this report.", ""])
        return "\n".join(lines)

    with logfire.span("generate_enriched_reports"):
        contents = await asyncio.gather(
            *[_enrich_finding(r, repo_path, model) for r in pipeline_report.reports]
        )
        for content in contents:
            lines.append("---")
            lines.append("")
            lines.append(content)
            lines.append("")

    return "\n".join(lines).rstrip()

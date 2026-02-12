"""Orchestrates report markdown generation: draft per section + optional agent enrichment."""

import asyncio
import logging
from pathlib import Path
from typing import Callable

from triage.agent.agents.report_formatter import create_report_formatter_agent
from triage.agent.deps import BaseDeps
from triage.models.pipeline import PipelineReport, TriagePipelineReport
from triage.report.markdown_report import (
    _compact_assumptions,
    _compact_counterexample,
    _compact_evidence,
    _compact_header,
    _compact_sanitizers,
    _compact_trace,
    render_pipeline_report_markdown,
)

logger = logging.getLogger(__name__)

# Drafts that are placeholders with no code to enrich; skip agent to avoid spurious read_file_lines calls.
_PLACEHOLDER_MARKERS = ("none found",)
_PLACEHOLDER_MAX_LEN = 250  # Short draft with only placeholder text


def _is_placeholder_draft(draft_text: str) -> bool:
    """True if the section is just a placeholder with nothing to enrich."""
    t = draft_text.strip()
    if not t or len(t) > _PLACEHOLDER_MAX_LEN:
        return False
    lower = t.lower()
    return any(m in lower for m in _PLACEHOLDER_MARKERS)


SECTION_ORDER: list[tuple[str, Callable[[TriagePipelineReport], list[str]]]] = [
    ("Header", lambda r: _compact_header(r)),
    ("Trace", lambda r: _compact_trace(r.source_to_sink_trace)),
    ("Sanitizers", lambda r: _compact_sanitizers(r.sanitizers_validators)),
    ("Evidence", lambda r: _compact_evidence(r.evidence_pack)),
    ("Assumptions", lambda r: _compact_assumptions(r.explicit_assumptions)),
    ("Counterexample", lambda r: _compact_counterexample(r)),
]


async def _enrich_section(
    section_name: str,
    draft_text: str,
    repo_path: Path,
    model: str,
) -> str:
    """Run the report formatter agent on one section; return draft on failure or if empty/placeholder."""
    if not draft_text.strip():
        return draft_text
    if _is_placeholder_draft(draft_text):
        return draft_text
    agent = create_report_formatter_agent(model=model)
    deps = BaseDeps(repo_path=repo_path.resolve(), lsp=None)
    user_prompt = f"Section: {section_name}\n\nDraft:\n{draft_text}"
    try:
        result = await agent.run(user_prompt, deps=deps)
        return result.output.content
    except Exception as e:
        logger.warning("Report formatter failed for section %s: %s", section_name, e)
        return draft_text


async def generate_enriched_reports(
    pipeline_report: PipelineReport,
    repo_path: Path,
    model: str = "openai:gpt-5-mini",
    use_agent: bool = True,
) -> str:
    """Generate full pipeline report markdown. If use_agent is True, each section is improved by the formatter agent."""
    repo_path = repo_path.resolve()
    if not use_agent:
        return render_pipeline_report_markdown(pipeline_report)

    lines: list[str] = ["# Pipeline report", ""]
    if not pipeline_report.reports:
        lines.extend(["There are no findings in this report.", ""])
        return "\n".join(lines)

    for r in pipeline_report.reports:
        lines.append("---")
        lines.append("")
        coros = [
            _enrich_section(section_name, "\n".join(section_fn(r)), repo_path, model)
            for section_name, section_fn in SECTION_ORDER
        ]
        results = await asyncio.gather(*coros)
        for content in results:
            lines.append(content)
            lines.append("")

    return "\n".join(lines).rstrip()

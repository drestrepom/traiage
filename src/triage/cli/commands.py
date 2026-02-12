import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import click

from triage.agent.orchestrator import triage_finding
from triage.agent.tools import start_lsp_client
from triage.models import load_findings
from triage.models.pipeline import PipelineReport, TriagePipelineReport
from triage.models.vulnerability import Vulnerability
from triage.report.enricher import generate_enriched_reports
from triage.report.html_report import (
    write_html_from_markdown,
    write_pipeline_report_html,
)
from triage.report.json_report import write_pipeline_report
from triage.report.markdown_report import (
    write_pipeline_report_markdown,
)

import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# Set to False to disable LSP server (LSP shutdown hangs, so we force exit)
ENABLE_LSP = True


async def _run_pipeline_findings(
    repo_path: Path,
    vulnerabilities: list[Vulnerability],
    concurrency: int,
    lsp: Any = None,
) -> list[TriagePipelineReport]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[TriagePipelineReport | None] = [None] * len(vulnerabilities)

    async def run_and_store(
        idx: int, vuln: Vulnerability
    ) -> tuple[int, TriagePipelineReport]:
        async with semaphore:
            report = await triage_finding(vuln, repo_path, lsp=lsp)
        return idx, report

    tasks = [run_and_store(i, v) for i, v in enumerate(vulnerabilities)]
    for coro in asyncio.as_completed(tasks):
        idx, report = await coro
        results[idx] = report
    return results  # type: ignore[return-value]


@click.group()
def cli() -> None:
    """Triage SAST findings (single agent or multi-agent pipeline)."""


@click.command("run-pipeline")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Path to the repository to analyze.",
)
@click.option(
    "--findings-path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the JSON file with vulnerabilities (findings).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Base path for output files (default: report). Generates report.json, report.md, report.html.",
)
@click.option(
    "--concurrency",
    type=int,
    default=5,
    help="Max concurrent pipeline runs per finding (default 1; use 1 when LSP is enabled).",
)
@click.option(
    "--no-enrich",
    is_flag=True,
    default=False,
    help="Skip agent-based report enrichment; output plain markdown/html from templates.",
)
def run_pipeline(
    repo_path: Path,
    findings_path: Path,
    output: Path | None,
    concurrency: int,
    no_enrich: bool,
) -> None:
    """Run the multi-agent pipeline (A0–A6) for each finding."""
    repo_path = repo_path.resolve()
    findings = load_findings(findings_path.resolve())
    findings_list = findings.vulnerabilities

    async def _run_with_lsp() -> list[TriagePipelineReport]:
        async with start_lsp_client(repo_path) as lsp:
            return await _run_pipeline_findings(
                repo_path, findings_list, concurrency, lsp=lsp
            )

    async def _run_without_lsp() -> list[TriagePipelineReport]:
        return await _run_pipeline_findings(
            repo_path, findings_list, concurrency, lsp=None
        )

    if not findings_list:
        pipeline_report = PipelineReport(reports=[])
    elif ENABLE_LSP:
        results = asyncio.run(_run_with_lsp())
        pipeline_report = PipelineReport(reports=results)
    else:
        logger.info("LSP disabled (ENABLE_LSP=False)")
        results = asyncio.run(_run_without_lsp())
        pipeline_report = PipelineReport(reports=results)

    out_base = output or Path("report")
    out_base = out_base.resolve()
    if out_base.suffix in (".json", ".md", ".html"):
        out_base = out_base.with_suffix("")
    write_pipeline_report(pipeline_report, out_base.with_suffix(".json"))
    if no_enrich:
        write_pipeline_report_markdown(pipeline_report, out_base.with_suffix(".md"))
        write_pipeline_report_html(pipeline_report, out_base.with_suffix(".html"))
    else:
        md_content = asyncio.run(
            generate_enriched_reports(pipeline_report, repo_path, use_agent=True)
        )
        out_base.with_suffix(".md").write_text(md_content, encoding="utf-8")
        write_html_from_markdown(md_content, out_base.with_suffix(".html"))
    click.echo(
        f"Pipeline report written to {out_base.with_suffix('.json')}, "
        f"{out_base.with_suffix('.md')}, {out_base.with_suffix('.html')}"
    )

    logfire.shutdown(timeout_millis=3000, flush=True)


@click.command("convert-report")
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the pipeline report JSON file.",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Base path for output files. Default: same name as input. Writes report.md and report.html.",
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Repository root (required for --enrich so the agent can read source files).",
)
@click.option(
    "--enrich",
    is_flag=True,
    default=False,
    help="Use the report formatter agent to enrich markdown/html with inlined code from the repo.",
)
def convert_report(
    input_path: Path,
    output_path: Path | None,
    repo_path: Path | None,
    enrich: bool,
) -> None:
    """Convert an existing pipeline JSON report to Markdown and HTML."""
    input_path = input_path.resolve()
    data = json.loads(input_path.read_text(encoding="utf-8"))
    report = PipelineReport.model_validate(data)
    out_base = output_path or input_path.with_suffix("")
    if out_base.suffix in (".json", ".md", ".html"):
        out_base = out_base.with_suffix("")
    out_base = out_base.resolve()

    if enrich:
        if repo_path is None:
            raise click.UsageError("--repo-path is required when using --enrich")
        repo_path = repo_path.resolve()
        md_content = asyncio.run(
            generate_enriched_reports(report, repo_path, use_agent=True)
        )
        out_base.with_suffix(".md").write_text(md_content, encoding="utf-8")
        write_html_from_markdown(md_content, out_base.with_suffix(".html"))
        click.echo(
            f"Enriched report written to {out_base.with_suffix('.md')}, "
            f"{out_base.with_suffix('.html')}"
        )
    else:
        write_pipeline_report_markdown(report, out_base.with_suffix(".md"))
        write_pipeline_report_html(report, out_base.with_suffix(".html"))
        click.echo(
            f"Report written to {out_base.with_suffix('.md')}, "
            f"{out_base.with_suffix('.html')}"
        )


cli.add_command(run_pipeline)
cli.add_command(convert_report)

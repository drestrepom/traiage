from pathlib import Path

from triage.models.pipeline import PipelineReport


def write_pipeline_report(report: PipelineReport, path: Path) -> None:
    path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

from pathlib import Path
import subprocess

from triage.models.pipeline import PipelineReport
from triage.report.markdown_report import render_pipeline_report_markdown

# CSS overrides to use more of the page and reduce empty margins (pandoc default is narrow)
_LAYOUT_CSS = """
    body {
      max-width: 90%;
      margin: 0 auto;
      padding: 1rem 2rem;
    }
    pre, code { overflow-x: auto; }
"""


def write_html_from_markdown(md_text: str, path: Path) -> None:
    try:
        subprocess.run(
            [
                "pandoc",
                "--from=markdown+fenced_code_blocks+pipe_tables",
                "--to=html5",
                "--standalone",
                "--metadata=title:Pipeline report",
                "--output",
                str(path),
            ],
            input=md_text,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pandoc is not installed or not available in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown pandoc error"
        raise RuntimeError(f"Failed to generate HTML with pandoc: {stderr}") from exc

    # Override pandoc's narrow default layout so the report uses more of the page
    html = path.read_text(encoding="utf-8")
    if "</style>" in html:
        html = html.replace("</style>", f"{_LAYOUT_CSS}\n  </style>", 1)
        path.write_text(html, encoding="utf-8")


def write_pipeline_report_html(report: PipelineReport, path: Path) -> None:
    """Write an HTML report from a PipelineReport (Markdown converted to HTML)."""
    md_text = render_pipeline_report_markdown(report)
    write_html_from_markdown(md_text, path)

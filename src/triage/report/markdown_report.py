from pathlib import Path

from triage.models.pipeline import (
    AssumptionsResult,
    EvidencePack,
    MitigationsResult,
    PipelineReport,
    TriagePipelineReport,
    TraceResult,
    VerdictPipeline,
)


def _compact_header(r: TriagePipelineReport) -> list[str]:
    """Merged finding header + verdict + severity + confidence."""
    f = r.finding
    v = r.verdict

    verdict_label = {
        VerdictPipeline.TRUE_VULNERABILITY: "TP",
        VerdictPipeline.FALSE_POSITIVE: "FP",
        VerdictPipeline.INCONCLUSIVE: "Inconclusive",
    }.get(v.verdict, v.verdict.value)

    # Confidence: prefer verdict.confidence, fall back to trace, then severity
    conf = v.confidence
    if not conf and r.source_to_sink_trace:
        conf = r.source_to_sink_trace.confidence
    if not conf and r.severity_priority:
        conf = r.severity_priority.confidence

    # Build the status line
    parts = [f"Verdict: **{verdict_label}**"]

    s = r.severity_priority
    if s and v.verdict == VerdictPipeline.TRUE_VULNERABILITY:
        if s.severity:
            parts.append(f"Severity: {s.severity}")
        if s.priority:
            parts.append(f"Priority: {s.priority}")

    if conf:
        parts.append(f"Confidence: {conf:.2f}")

    status_line = " — ".join(parts)

    lines = [
        f"## Finding: {f.id} ({f.type})",
        "",
        status_line,
        "",
    ]

    if v.reasoning:
        lines.extend([v.reasoning, ""])

    return lines


def _compact_trace(trace: TraceResult | None) -> list[str]:
    """One line per PathStep, gaps as single line."""
    if not trace or not trace.paths:
        return []
    lines = ["### Trace (Source → Sink)", ""]
    for step in trace.paths:
        excerpt = ""
        if step.code_excerpt:
            first_line = step.code_excerpt.strip().split("\n")[0]
            excerpt = f": `{first_line[:80]}`" if first_line else ""
        func = step.function or "?"
        lines.append(
            f"- `{step.file}:{func}` L{step.start_line}–{step.end_line}{excerpt}"
        )
    if trace.gaps:
        lines.append(f"- Gaps: {'; '.join(trace.gaps)}")
    lines.append("")
    return lines


def _compact_sanitizers(m: MitigationsResult | None) -> list[str]:
    """Max 2 assessments, no per-citation sub-lists."""
    if not m or (not m.mitigations_found and not m.assessment_per_mitigation):
        return ["### Sanitizers on path", "", "None found.", ""]
    lines = ["### Sanitizers on path", ""]
    for assessment in m.assessment_per_mitigation[:2]:
        status_parts: list[str] = []
        if assessment.sufficient:
            status_parts.append("Sufficient")
        if assessment.insufficient:
            status_parts.append("Insufficient")
        if assessment.unknown:
            status_parts.append("Unknown")
        status = ", ".join(status_parts) if status_parts else "—"
        rationale = assessment.rationale[:120] if assessment.rationale else ""
        lines.append(f"- {status}: {rationale}")
    lines.append("")
    return lines


def _compact_evidence(ep: EvidencePack | None) -> list[str]:
    """Show max 2 snippets: source and sink."""
    if not ep or not ep.snippets:
        return []
    lines = ["### Evidence", ""]

    # Pick source and sink snippets by purpose or position
    snippets = ep.snippets
    source_snippet = None
    sink_snippet = None
    for s in snippets:
        lower_purpose = s.purpose.lower()
        if "source" in lower_purpose and not source_snippet:
            source_snippet = s
        elif "sink" in lower_purpose and not sink_snippet:
            sink_snippet = s
    if not source_snippet and len(snippets) >= 1:
        source_snippet = snippets[0]
    if not sink_snippet and len(snippets) >= 2:
        sink_snippet = snippets[-1]
    # Avoid duplicates
    if source_snippet and sink_snippet and source_snippet is sink_snippet:
        sink_snippet = None

    for label, snippet in [("Source", source_snippet), ("Sink", sink_snippet)]:
        if not snippet:
            continue
        lines.append(
            f"- {label} (`{snippet.file}` L{snippet.start_line}–{snippet.end_line}):"
        )
        if snippet.text:
            lines.append("  ```python")
            for code_line in snippet.text.strip().split("\n"):
                lines.append(f"  {code_line}")
            lines.append("  ```")
    lines.append("")
    return lines


def _compact_assumptions(a: AssumptionsResult | None) -> list[str]:
    """Max 4 bullets, no category labels, no inline citations."""
    if not a or not a.assumptions:
        return []
    lines = ["### Assumptions", ""]
    for assump in a.assumptions[:4]:
        lines.append(f"- {assump.text}")
    lines.append("")
    return lines


def _compact_counterexample(r: TriagePipelineReport) -> list[str]:
    """Only render if verdict == FP and counterexample exists."""
    if r.verdict.verdict != VerdictPipeline.FALSE_POSITIVE:
        return []
    ce = r.minimal_counterexample
    if not ce:
        return []
    lines = ["### Counterexample", ""]
    c = ce.counterexample
    if c.type:
        lines.append(f"- **Type:** {c.type}")
    if c.explanation:
        lines.append(f"- {c.explanation}")
    if ce.fp_mechanism:
        lines.append(f"- **FP Mechanism:** {ce.fp_mechanism}")
    lines.append("")
    return lines


def _compact_fix(r: TriagePipelineReport) -> list[str]:
    """Single optional line for suggested fix."""
    s = r.severity_priority
    if s and s.suggested_fix:
        return [f"**Suggested fix:** {s.suggested_fix}", ""]
    return []


def _render_single_report(r: TriagePipelineReport) -> list[str]:
    parts: list[list[str]] = [
        _compact_header(r),
        _compact_trace(r.source_to_sink_trace),
        _compact_sanitizers(r.sanitizers_validators),
        _compact_evidence(r.evidence_pack),
        _compact_assumptions(r.explicit_assumptions),
        _compact_counterexample(r),
        _compact_fix(r),
    ]
    return [line for block in parts for line in block]


def render_pipeline_report_markdown(report: PipelineReport) -> str:
    """Return the pipeline report as a Markdown string."""
    lines: list[str] = [
        "# Pipeline report",
        "",
    ]
    if not report.reports:
        lines.extend(["There are no findings in this report.", ""])
    else:
        for r in report.reports:
            lines.append("---")
            lines.append("")
            lines.extend(_render_single_report(r))
    return "\n".join(lines)


def write_pipeline_report_markdown(report: PipelineReport, path: Path) -> None:
    """Write a human-readable Markdown report from a PipelineReport."""
    path.write_text(render_pipeline_report_markdown(report), encoding="utf-8")

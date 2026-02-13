from dataclasses import dataclass
from pathlib import Path
from typing import Any


from triage.models.pipeline import (
    AssumptionsResult,
    EvidencePack,
    MitigationsResult,
    TraceResult,
    VerdictResult,
)
from triage.models.vulnerability import Vulnerability


@dataclass
class BaseDeps:
    repo_path: Path
    lsp: Any


@dataclass
class AgentDeps(BaseDeps):
    vulnerability: Vulnerability


@dataclass
class PipelineDeps(BaseDeps):
    """Deps for pipeline agents A1–A6; orquestador fills fields per stage."""

    finding: Vulnerability
    evidence_pack: EvidencePack | None = None
    trace: TraceResult | None = None
    mitigations: MitigationsResult | None = None
    assumptions: AssumptionsResult | None = None
    verdict: VerdictResult | None = None

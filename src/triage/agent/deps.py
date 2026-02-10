from dataclasses import dataclass
from pathlib import Path

from lsp_client.clients import PyrightClient

from triage.models.vulnerability import Vulnerability


@dataclass
class AgentDeps:
    repo_path: Path
    vulnerability: Vulnerability
    lsp: PyrightClient = None

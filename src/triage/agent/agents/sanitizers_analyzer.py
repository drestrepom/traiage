from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A2_SANITIZERS_ANALYZER
from triage.agent.tools import (
    GREP_TOOL,
    LSP_DOCUMENT_SYMBOL_TOOL,
    LSP_FIND_REFERENCES_TOOL,
    LSP_GO_TO_DEFINITION_TOOL,
    LSP_HOVER_TOOL,
)
from triage.models.pipeline import MitigationsResult


def create_sanitizers_analyzer_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, MitigationsResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=MitigationsResult,
        system_prompt=SYSTEM_PROMPT_A2_SANITIZERS_ANALYZER,
        tools=[
            GREP_TOOL,
            LSP_GO_TO_DEFINITION_TOOL,
            LSP_FIND_REFERENCES_TOOL,
            LSP_HOVER_TOOL,
            LSP_DOCUMENT_SYMBOL_TOOL,
        ],
    )

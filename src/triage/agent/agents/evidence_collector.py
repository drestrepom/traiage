from pydantic_ai import Agent

from triage.agent.deps import AgentDeps
from triage.agent.prompts import SYSTEM_PROMPT_A0_EVIDENCE_COLLECTOR
from triage.agent.tools import (
    GREP_TOOL,
    LIST_FILES_TOOL,
    LSP_DOCUMENT_SYMBOL_TOOL,
    LSP_FIND_REFERENCES_TOOL,
    LSP_GO_TO_DEFINITION_TOOL,
    LSP_HOVER_TOOL,
    READ_FILE_TOOL,
)
from triage.models.pipeline import EvidencePack
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="medium",
)


def create_evidence_collector_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[AgentDeps, EvidencePack]:
    return Agent(
        model,
        deps_type=AgentDeps,
        output_type=EvidencePack,
        system_prompt=SYSTEM_PROMPT_A0_EVIDENCE_COLLECTOR,
        tools=[
            LIST_FILES_TOOL,
            READ_FILE_TOOL,
            GREP_TOOL,
            LSP_GO_TO_DEFINITION_TOOL,
            LSP_FIND_REFERENCES_TOOL,
            LSP_HOVER_TOOL,
            LSP_DOCUMENT_SYMBOL_TOOL,
        ],
        model_settings=settings,
        retries=3,
        tool_timeout=10,
    )

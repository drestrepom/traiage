from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A1_SOURCE_SINK_TRACER
from triage.agent.tools import (
    GREP_TOOL,
    LSP_DOCUMENT_SYMBOL_TOOL,
    LSP_FIND_REFERENCES_TOOL,
    LSP_GO_TO_DEFINITION_TOOL,
    LSP_HOVER_TOOL,
)
from triage.models.pipeline import TraceResult


def create_source_sink_tracer_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, TraceResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=TraceResult,
        system_prompt=SYSTEM_PROMPT_A1_SOURCE_SINK_TRACER,
        tools=[
            GREP_TOOL,
            LSP_GO_TO_DEFINITION_TOOL,
            LSP_FIND_REFERENCES_TOOL,
            LSP_HOVER_TOOL,
            LSP_DOCUMENT_SYMBOL_TOOL,
        ],
    )

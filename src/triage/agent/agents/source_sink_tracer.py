from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A1_SOURCE_SINK_TRACER
from triage.agent.tools import (
    GET_FUNCTION_CODE_TOOL,
    GREP_TOOL,
    LIST_FILES_TOOL,
)
from triage.models.pipeline import TraceResult
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
)


def create_source_sink_tracer_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, TraceResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=TraceResult,
        system_prompt=SYSTEM_PROMPT_A1_SOURCE_SINK_TRACER,
        tools=[GREP_TOOL, LIST_FILES_TOOL, GET_FUNCTION_CODE_TOOL],
        model_settings=settings,
    )

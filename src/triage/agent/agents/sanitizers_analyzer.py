from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A2_SANITIZERS_ANALYZER
from triage.agent.tools import (
    GET_FUNCTION_CODE_TOOL,
    GREP_TOOL,
    LIST_FILES_TOOL,
)
from triage.models.pipeline import MitigationsResult
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
)


def create_sanitizers_analyzer_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, MitigationsResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=MitigationsResult,
        system_prompt=SYSTEM_PROMPT_A2_SANITIZERS_ANALYZER,
        tools=[GREP_TOOL, LIST_FILES_TOOL, GET_FUNCTION_CODE_TOOL],
        model_settings=settings,
    )

from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A6_SEVERITY_RATER
from triage.models.pipeline import SeverityResult
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
)


def create_severity_rater_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, SeverityResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=SeverityResult,
        system_prompt=SYSTEM_PROMPT_A6_SEVERITY_RATER,
        tools=[],
        model_settings=settings,
    )

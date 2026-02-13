from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A3_ASSUMPTIONS_EXTRACTOR
from triage.models.pipeline import AssumptionsResult
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
)


def create_assumptions_extractor_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, AssumptionsResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=AssumptionsResult,
        system_prompt=SYSTEM_PROMPT_A3_ASSUMPTIONS_EXTRACTOR,
        tools=[],
        model_settings=settings,
    )

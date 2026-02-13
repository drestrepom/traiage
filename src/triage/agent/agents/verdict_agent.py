from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A5_VERDICT_AGENT
from triage.models.pipeline import VerdictResult
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
)


def create_verdict_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, VerdictResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=VerdictResult,
        system_prompt=SYSTEM_PROMPT_A5_VERDICT_AGENT,
        tools=[],
        model_settings=settings,
    )

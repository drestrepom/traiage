from pydantic_ai import Agent

from triage.agent.deps import PipelineDeps
from triage.agent.prompts import SYSTEM_PROMPT_A4_COUNTEREXAMPLE_BUILDER
from triage.models.pipeline import CounterexampleResult


def create_counterexample_builder_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[PipelineDeps, CounterexampleResult]:
    return Agent(
        model,
        deps_type=PipelineDeps,
        output_type=CounterexampleResult,
        system_prompt=SYSTEM_PROMPT_A4_COUNTEREXAMPLE_BUILDER,
        tools=[],
    )

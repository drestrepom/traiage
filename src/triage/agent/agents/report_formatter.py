from pydantic import BaseModel, Field
from pydantic_ai import Agent

from triage.agent.deps import BaseDeps
from triage.agent.prompts import SYSTEM_PROMPT_A7_REPORT_FORMATTER
from triage.agent.tools import LIST_FILES_TOOL, READ_FILE_LINES_TOOL

from pydantic_ai.models.openai import OpenAIResponsesModelSettings


class ReportContent(BaseModel):
    """Improved markdown content for one report section."""

    content: str = Field(..., description="The formatted markdown for this section.")


settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
)


def create_report_formatter_agent(
    model: str = "openai:gpt-5-mini",
) -> Agent[BaseDeps, ReportContent]:
    return Agent(
        model,
        deps_type=BaseDeps,
        output_type=ReportContent,
        system_prompt=SYSTEM_PROMPT_A7_REPORT_FORMATTER,
        tools=[LIST_FILES_TOOL, READ_FILE_LINES_TOOL],
        model_settings=settings,
    )

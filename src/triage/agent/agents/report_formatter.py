from pydantic import BaseModel, Field
from pydantic_ai import Agent

from triage.agent.deps import BaseDeps
from triage.agent.prompts import SYSTEM_PROMPT_A7_REPORT_FORMATTER
from triage.agent.tools import (
    GREP_TOOL,
    LIST_FILES_TOOL,
    READ_FILE_LINES_TOOL,
    SEARCH_OWASP_TOOL,
)

from pydantic_ai.models.openai import OpenAIResponsesModelSettings


class ReportContent(BaseModel):
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
        tools=[LIST_FILES_TOOL, READ_FILE_LINES_TOOL, SEARCH_OWASP_TOOL, GREP_TOOL],
        model_settings=settings,
    )

from pydantic_ai import Agent

from triage.agent.deps import AgentDeps
from triage.agent.tools import (
    LIST_FILES_TOOL,
    LSP_DOCUMENT_SYMBOL_TOOL,
    LSP_FIND_REFERENCES_TOOL,
    LSP_GO_TO_DEFINITION_TOOL,
    LSP_HOVER_TOOL,
    READ_FILE_TOOL,
    GREP_TOOL,
)
from triage.models.report import FindingResult

SYSTEM_PROMPT = (
    "You are a security analyst validating one SAST finding on Python code. "
    "You have access to the repository path and one reported vulnerability. "
    "You can list and read files, search text in the codebase, jump to definitions, "
    "find references, get hover information, and explore document and workspace symbols. "
    "Determine whether this finding is a True Positive (real vulnerability) or False Positive. "
    "Base your analysis on OWASP knowledge and the code you read."
)


def create_agent(model: str = "openai:gpt-5-mini") -> Agent[AgentDeps, FindingResult]:
    return Agent(
        model,
        deps_type=AgentDeps,
        output_type=FindingResult,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            LIST_FILES_TOOL,
            # READ_FILE_TOOL,
            GREP_TOOL,
            LSP_GO_TO_DEFINITION_TOOL,
            LSP_FIND_REFERENCES_TOOL,
            LSP_HOVER_TOOL,
            LSP_DOCUMENT_SYMBOL_TOOL,
        ],
    )

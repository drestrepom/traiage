from pydantic_ai import Agent

from triage.agent.deps import AgentDeps
from triage.agent.tools import (
    LIST_FILES_TOOL,
    LSP_DOCUMENT_SYMBOL_TOOL,
    LSP_FIND_REFERENCES_TOOL,
    LSP_GO_TO_DEFINITION_TOOL,
    LSP_HOVER_TOOL,
    LSP_WORKSPACE_SYMBOL_TOOL,
    READ_FILE_TOOL,
    GREP_TOOL,
)
from triage.models.report import FindingResult

SYSTEM_PROMPT = (
    "You are a security analyst validating one SAST finding on Python code. "
    "You have access to the repository path and one reported vulnerability. "
    "Use the list_files, read_file, and grep tools to inspect the code. "
    "You can also use LSP tools for definitions (lsp_go_to_definition), references (lsp_find_references), "
    "hover (lsp_hover), document symbols (lsp_document_symbol), and workspace symbol search (lsp_workspace_symbol). "
    "Determine whether this finding is a True Positive (real vulnerability) or False Positive. "
    "Return a FindingResult: finding_id (same id as the input finding), "
    "verdict exactly 'True Positive' or 'False Positive', and justification (brief, with code references). "
    "Base your analysis on OWASP knowledge and the code you read."
)


def create_agent(model: str = "openai:gpt-4o-mini") -> Agent[AgentDeps, FindingResult]:
    return Agent(
        model,
        deps_type=AgentDeps,
        output_type=FindingResult,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            LIST_FILES_TOOL,
            READ_FILE_TOOL,
            GREP_TOOL,
            LSP_GO_TO_DEFINITION_TOOL,
            LSP_FIND_REFERENCES_TOOL,
            LSP_HOVER_TOOL,
            LSP_DOCUMENT_SYMBOL_TOOL,
            LSP_WORKSPACE_SYMBOL_TOOL,
        ],
    )

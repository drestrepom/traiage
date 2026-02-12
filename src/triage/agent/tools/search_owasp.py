from pydantic_ai import RunContext, Tool

from triage.agent.deps import BaseDeps
from triage.owasp.store import OWASPStore


async def _search_owasp(_ctx: RunContext[BaseDeps], query: str) -> str:
    """Search the OWASP Top 10 2025 vector database for relevant documents.

    Args:
        _ctx: Run context (required by Pydantic AI tool system).
        query: Search query (e.g., "SQL injection mitigation", "access control").

    Returns:
        Formatted markdown string with top-3 results, or a message if the DB is not indexed.
    """
    if not query.strip():
        return "Query is required."

    try:
        # Embed the query
        from pydantic_ai import Embedder

        embedder = Embedder("openai:text-embedding-3-small")
        embedding_response = await embedder.embed_documents([query])
        query_vector = list(embedding_response.embeddings[0])

        # Search the store
        store = OWASPStore()
        results = store.search(query_vector, limit=3)

        if not results:
            return (
                "No OWASP documents found. "
                "Run `triage build-owasp-db` to index the OWASP Top 10 2025 documents."
            )

        # Format results
        lines: list[str] = ["**OWASP Top 10 2025 References:**"]
        for i, result in enumerate(results, 1):
            filename = result.get("filename", "unknown")
            score = result.get("distance", 0.0)
            url = result.get("owasp_url", "#")
            content = result.get("text", "")

            lines.append(f"\n{i}. **{filename}** (similarity: {score:.2f})")
            lines.append(f"   URL: {url}")
            # Include first 200 chars of content as preview
            if content:
                preview = content[:200].replace("\n", " ").strip()
                if len(content) > 200:
                    preview += "..."
                lines.append(f"   Preview: {preview}")

        return "\n".join(lines)

    except FileNotFoundError:
        return (
            "OWASP database not found. "
            "Run `triage build-owasp-db` to index the OWASP Top 10 2025 documents."
        )
    except Exception as e:
        # Gracefully handle any errors (e.g., DB corruption, missing collection)
        return (
            f"Could not search OWASP database: {e}. "
            "Run `triage build-owasp-db` to re-index the documents."
        )


SEARCH_OWASP_TOOL = Tool(
    _search_owasp,
    name="search_owasp",
    description=(
        "Search the OWASP Top 10 2025 vector database for relevant vulnerability categories. "
        "Use this to find OWASP references when documenting findings related to common attack patterns. "
        "Accepts a short query like 'SQL injection', 'broken access control', 'SSRF', etc. "
        "Returns top-3 matching OWASP documents with URLs and preview content. "
        "Returns a helpful message if the database has not been indexed yet."
    ),
    takes_ctx=True,
)

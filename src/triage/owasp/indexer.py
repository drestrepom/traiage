import os
from pathlib import Path

from pydantic_ai import Embedder

from triage.owasp.store import OWASPStore


async def index_owasp_docs(
    docs_path: Path | str | None = None,
    db_path: Path | str | None = None,
    force_reindex: bool = False,
) -> int:
    # Resolve docs_path
    if docs_path is None:
        docs_path = os.getenv("OWASP_DOCS_PATH")
        if not docs_path:
            raise ValueError(
                "docs_path is required and OWASP_DOCS_PATH env var is not set"
            )
    docs_path = Path(docs_path)

    if not docs_path.is_dir():
        raise FileNotFoundError(f"OWASP docs directory not found: {docs_path}")

    # Collect markdown files
    md_files = sorted(docs_path.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No *.md files found in {docs_path}")

    # Initialize store
    store = OWASPStore(db_path)

    if force_reindex:
        store.drop_collection()

    # Read documents
    docs_text: list[str] = []
    docs_meta: list[dict[str, str]] = []

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        filename = md_file.name
        owasp_url = _filename_to_owasp_url(filename)
        docs_text.append(text)
        docs_meta.append(
            {
                "filename": filename,
                "owasp_url": owasp_url,
            }
        )

    # Embed documents
    embedder = Embedder("openai:text-embedding-3-small")
    embeddings_response = await embedder.embed_documents(docs_text)
    embeddings = embeddings_response.embeddings

    # Insert into store
    records = []
    for text, meta, embedding in zip(docs_text, docs_meta, embeddings):
        records.append(
            {
                "vector": list(embedding),
                "text": text,
                "filename": meta["filename"],
                "owasp_url": meta["owasp_url"],
            }
        )

    count = store.insert(records)
    return count


def _filename_to_owasp_url(filename: str) -> str:
    # Remove .md extension
    if filename.endswith(".md"):
        filename = filename[:-3]

    return f"https://owasp.org/Top10/2025/{filename}/"

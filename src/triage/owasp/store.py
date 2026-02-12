import os
from pathlib import Path
from typing import Any

from pymilvus import MilvusClient


class OWASPStore:
    """Wrapper around MilvusClient for OWASP Top 10 vector database."""

    COLLECTION_NAME = "owasp_top10"
    EMBEDDING_DIM = 1536
    METRIC_TYPE = "COSINE"

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initialize the OWASP store with a local Milvus Lite database.

        Args:
            db_path: Path to the database file. If None, uses $OWASP_DB_PATH or
                    ~/.local/share/triage/owasp.db
        """
        if db_path is None:
            db_path = os.getenv(
                "OWASP_DB_PATH",
                str(Path.home() / ".local" / "share" / "triage" / "owasp.db"),
            )
        self.db_path = Path(db_path)
        self.client = MilvusClient(str(self.db_path))

    def ensure_collection(self) -> None:
        """Ensure the owasp_top10 collection exists."""
        if self.client.has_collection(self.COLLECTION_NAME):
            return

        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            dimension=self.EMBEDDING_DIM,
            metric_type=self.METRIC_TYPE,
            auto_id=True,
            enable_dynamic_field=True,
        )

    def drop_collection(self) -> None:
        """Drop the owasp_top10 collection if it exists."""
        if self.client.has_collection(self.COLLECTION_NAME):
            self.client.drop_collection(self.COLLECTION_NAME)

    def insert(self, records: list[dict[str, Any]]) -> int:
        """Insert records into the collection.

        Args:
            records: List of dicts with keys:
                    - vector: list[float] (embedding)
                    - text: str (content)
                    - filename: str (source filename)
                    - owasp_url: str (OWASP reference URL)

        Returns:
            Number of records inserted.
        """
        if not records:
            return 0

        self.ensure_collection()
        result = self.client.insert(self.COLLECTION_NAME, records)
        return len(result.get("insert_count", 0)) if result else 0

    def search(
        self, vector: list[float], limit: int = 3
    ) -> list[dict[str, Any]]:
        """Search for similar documents.

        Args:
            vector: Query embedding (list of floats).
            limit: Number of results to return.

        Returns:
            List of dicts with fields: text, filename, owasp_url, distance.
            Empty list if collection doesn't exist.
        """
        if not self.client.has_collection(self.COLLECTION_NAME):
            return []

        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            data=[vector],
            limit=limit,
            output_fields=["text", "filename", "owasp_url"],
        )

        if not results or not results[0]:
            return []

        output = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            output.append(
                {
                    "text": entity.get("text", ""),
                    "filename": entity.get("filename", ""),
                    "owasp_url": entity.get("owasp_url", ""),
                    "distance": hit.get("distance", 0.0),
                }
            )
        return output

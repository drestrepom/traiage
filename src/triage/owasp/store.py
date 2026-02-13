import json
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np


class OWASPStore:
    _INDEX_FILE = "index.json"

    def __init__(self, store_path: Path | str | None = None) -> None:
        if store_path is None:
            base = Path(
                os.getenv(
                    "OWASP_DB_PATH",
                    str(Path.home() / ".local" / "share" / "triage"),
                )
            )
        else:
            base = Path(store_path).parent
        self._workspace = base / "owasp_vectordb"
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._index_path = self._workspace / self._INDEX_FILE
        self._records: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        if not self._index_path.exists():
            return
        try:
            with self._index_path.open() as fh:
                data = json.load(fh)
            self._records = data
            if self._records:
                self._embeddings = np.array(
                    [r["vector"] for r in self._records], dtype=np.float32
                )
        except Exception:
            self._records = []
            self._embeddings = None

    def _save(self) -> None:
        with self._index_path.open("w") as fh:
            json.dump(self._records, fh)

    def drop_collection(self) -> None:
        shutil.rmtree(self._workspace, ignore_errors=True)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._index_path = self._workspace / self._INDEX_FILE
        self._records = []
        self._embeddings = None

    def insert(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        self._records.extend(records)
        self._embeddings = np.array(
            [r["vector"] for r in self._records], dtype=np.float32
        )
        self._save()
        return len(records)

    def search(self, vector: list[float], limit: int = 3) -> list[dict[str, Any]]:
        if self._embeddings is None or len(self._records) == 0:
            return []
        try:
            q = np.array(vector, dtype=np.float32)
            q_norm = np.linalg.norm(q)
            if q_norm == 0:
                return []
            norms = np.linalg.norm(self._embeddings, axis=1)
            dots = self._embeddings @ q
            with np.errstate(divide="ignore", invalid="ignore"):
                sims = np.where(norms > 0, dots / (norms * q_norm), 0.0)
            top_k = int(min(limit, len(self._records)))
            indices = np.argsort(sims)[::-1][:top_k]
            return [
                {
                    "text": self._records[i]["text"],
                    "filename": self._records[i]["filename"],
                    "owasp_url": self._records[i]["owasp_url"],
                    "distance": float(sims[i]),
                }
                for i in indices
            ]
        except Exception:
            return []

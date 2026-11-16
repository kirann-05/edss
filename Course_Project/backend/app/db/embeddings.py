"""Text to vectors, on this machine only (Lab 4, rule 7).

`OllamaEmbedder` asks a local embedding model (nomic-embed-text in development) and refuses any
server that is not local, whatever the data mode, so a brief's words never leave the machine.
`HashingEmbedder` needs no model: it hashes each word into a fixed-size vector. It is a stand-in,
good enough to find briefs that share words, and it keeps tests and an offline demo fast and
the same every time. Neither is ever given a figure, only the words of a brief.
"""

import hashlib
import math
import re
from urllib.parse import urlsplit

import httpx2

from app.agents.llm import is_local_host
from app.db.schema import EMBEDDING_DIMENSIONS

_WORD = re.compile(r"[a-z]+")


def _normalised(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / length for x in vector]


class HashingEmbedder:
    name = "hashing"

    def embed(self, texts: list[str], purpose: str = "document") -> list[list[float]]:
        out = []
        for text in texts:
            vector = [0.0] * EMBEDDING_DIMENSIONS
            for word in _WORD.findall(text.lower()):
                digest = hashlib.sha256(word.encode()).digest()
                index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
                vector[index] += 1.0 if digest[4] % 2 else -1.0
            out.append(_normalised(vector))
        return out


class OllamaEmbedder:
    """nomic-embed-text wants a task prefix, which is what `purpose` chooses."""

    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        if not is_local_host(base_url):
            raise ValueError(
                f"embeddings must stay on this machine, not {urlsplit(base_url).hostname}"
            )
        parts = urlsplit(base_url)
        self._url = f"{parts.scheme}://{parts.netloc}/api/embed"
        self._model, self._timeout = model, timeout
        self.name = f"ollama:{model}"

    def embed(self, texts: list[str], purpose: str = "document") -> list[list[float]]:
        prefix = "search_query: " if purpose == "query" else "search_document: "
        response = httpx2.post(
            self._url,
            json={"model": self._model, "input": [prefix + t for t in texts]},
            timeout=self._timeout,
        )
        response.raise_for_status()
        vectors = response.json()["embeddings"]
        if any(len(v) != EMBEDDING_DIMENSIONS for v in vectors):
            raise ValueError(f"{self._model} does not give {EMBEDDING_DIMENSIONS} dimensions")
        return [_normalised(v) for v in vectors]

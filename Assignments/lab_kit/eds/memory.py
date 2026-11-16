"""
Lab 4 - Memory & retrieval: short-term run state vs long-term stored knowledge.

    state.draft = candidate                        # short-term
    hits  = retrieve(store, tags)                   # long-term, by tag
    prior = retrieve(history, embed(candidate), k=5)  # long-term, by similarity

`RunState` holds the in-flight draft for the current run only -- it is
never persisted across runs. `LongTermStore` holds prior published
executive reports so future runs can retrieve similar past decisions
and their outcomes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


@dataclass
class RunState:
    """Short-term, in-flight state for the current run. Not persisted."""

    request: Dict[str, Any] = field(default_factory=dict)
    draft: Optional[Dict[str, Any]] = None
    scratch: Dict[str, Any] = field(default_factory=dict)

    def set_draft(self, candidate: Dict[str, Any]) -> None:
        self.draft = candidate


@dataclass
class StoredItem:
    id: str
    tags: List[str]
    text: str
    payload: Dict[str, Any]


class LongTermStore:
    """
    Long-term memory: tag-filterable and similarity-searchable history of
    past executive reports / decision briefs. Kept separate from
    `RunState` on purpose -- mixing the two corrupts the run's baseline.
    """

    def __init__(self):
        self._items: List[StoredItem] = []

    def add(self, item_id: str, tags: List[str], text: str, payload: Dict[str, Any]) -> None:
        self._items.append(StoredItem(id=item_id, tags=tags, text=text, payload=payload))

    def retrieve_by_tags(self, tags: List[str]) -> List[StoredItem]:
        wanted = set(tags)
        return [it for it in self._items if wanted & set(it.tags)]

    def retrieve_by_similarity(self, query_text: str, k: int = 5) -> List[StoredItem]:
        """A dependency-free stand-in for embedding similarity: Jaccard
        overlap of tokenized text. Swap for real embeddings later behind
        this same method signature."""
        q = _tokenize(query_text)
        scored = []
        for it in self._items:
            t = _tokenize(it.text)
            if not q or not t:
                score = 0.0
            else:
                score = len(q & t) / len(q | t)
            scored.append((score, it))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [it for score, it in scored[:k] if score > 0]

"""Where the data comes from, and reading it again.

With no folder configured the app generates the synthetic set, stamped relative to today. With a
folder (INGEST_DIR) it reads exports through the ingestion layer, and "Refresh data" reads the
folder again into the same ledger. Either way the rest of the system sees a DataStore and nothing
else (rule 6).

A refresh never renumbers anything. Records that were there keep their ids, so a brief approved
last month still points at the records it was written from.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.core.config import Settings
from app.ingestion.loader import Ledger
from app.ingestion.manifest import FolderResult, ManifestError, ingest_folder
from app.ingestion.validator import Reject
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.services.store import DataStore


class RefreshError(RuntimeError):
    """A refresh that could not be done. The data in use is untouched. The message says why."""


@dataclass(frozen=True)
class RefreshSummary:
    source: str  # "folder" or "synthetic"
    folder: str | None
    accepted: int
    rejected: int
    rejects: tuple[Reject, ...]  # the first few, for the screen
    unchanged_files: int


class DataSource:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ledger: Ledger | None = None

    @property
    def folder(self) -> Path | None:
        return Path(self._settings.ingest_dir) if self._settings.ingest_dir else None

    def _store_from(self, ledger: Ledger, today: date) -> DataStore:
        return DataStore(
            ledger.dataset(), load_seed_definitions(), load_seed_targets(), today,
            self._settings.stale_after_days,
        )  # fmt: skip

    def load(self, today: date) -> DataStore:
        """The store to start with."""
        folder = self.folder
        if folder is None:
            return DataStore.build(today, self._settings.stale_after_days)
        outcome = self._read(folder, today)
        if outcome.errors:
            raise RefreshError("; ".join(outcome.errors))
        return self._store_from(outcome.ledger, today)

    def refresh(self, today: date) -> tuple[DataStore, RefreshSummary]:
        folder = self.folder
        if folder is None:
            store = DataStore.build(today, self._settings.stale_after_days)
            facts = len(store.dataset.facts)
            return store, RefreshSummary("synthetic", None, facts, 0, (), 0)
        outcome = self._read(folder, today)
        if outcome.errors:
            raise RefreshError("; ".join(outcome.errors))
        unchanged = sum(1 for _, r in outcome.results if r.noop)
        summary = RefreshSummary(
            "folder", str(folder), outcome.accepted, outcome.rejected,
            tuple(r for _, res in outcome.results for r in res.rejects[:20])[:20], unchanged,
        )  # fmt: skip
        return self._store_from(outcome.ledger, today), summary

    def _read(self, folder: Path, today: date) -> FolderResult:
        try:
            outcome = ingest_folder(
                folder,
                today,
                data_mode=self._settings.data_mode,
                ingested_by="refresh",
                ledger=self._ledger,
            )
        except (ManifestError, FileNotFoundError) as error:
            raise RefreshError(str(error)) from None
        self._ledger = outcome.ledger  # kept, so the next refresh adds to it and ids stay put
        return outcome

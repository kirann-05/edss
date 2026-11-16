"""
Lab 5 - MCP-style connector: one governed surface for every data source.

No agent is allowed to touch a data source directly. Every agent reads
through a `Connector`, so swapping the backend (stub data today; a real
ERP / database / API tomorrow) never requires touching agent code.

    connector.expose:
        read('institutional KPIs & dashboards')
        read('department reports')
        read('external benchmarks')

This module ships one implementation, `StubConnector`, clearly marked as
a placeholder. To go live, implement the same `Connector` interface
against your real systems (e.g. `SqlConnector`, `CsvConnector`,
`ErpApiConnector`) and hand that instance to the Coordinator instead --
nothing else in this codebase changes.
"""

from __future__ import annotations

import abc
import copy
import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from data import stub_data


@dataclass
class AccessGrant:
    """Institution-level read access authorized by the Registrar (Gate 1)."""

    domain: str
    granted_by: str
    granted_at: str = field(default_factory=lambda: _dt.datetime.utcnow().isoformat())
    scope: str = "institution-wide read-only"


class AccessDeniedError(RuntimeError):
    pass


class Connector(abc.ABC):
    """The one governed surface every agent must use to reach data."""

    @abc.abstractmethod
    def request_access(self, domain: str, authorized_by: str) -> AccessGrant:
        ...

    @abc.abstractmethod
    def read(self, source: str, **kwargs) -> Any:
        ...


class StubConnector(Connector):
    """
    PLACEHOLDER connector backed by in-memory example data
    (see data/stub_data.py). Clearly not a real integration -- swap this
    class out for a real one behind the same `Connector` interface when
    the department systems are ready to be wired up.
    """

    SOURCES = {
        "institutional KPIs & dashboards": "kpi_definitions",
        "department reports": "department_reports",
        "external benchmarks": "external_benchmarks",
    }

    def __init__(self):
        self._grants: Dict[str, AccessGrant] = {}

    # -- Gate 1: access intake -------------------------------------------------
    def request_access(self, domain: str, authorized_by: str) -> AccessGrant:
        grant = AccessGrant(domain=domain, granted_by=authorized_by)
        self._grants[domain] = grant
        return grant

    def _require_access(self, domain: str) -> None:
        if domain not in self._grants:
            raise AccessDeniedError(
                f"No institution-level read access granted for domain='{domain}'. "
                f"Call request_access() first (Gate 1: access intake)."
            )

    # -- typed reads -------------------------------------------------------
    def read(self, source: str, **kwargs) -> Any:
        if source not in self.SOURCES:
            raise ValueError(f"Unknown source '{source}'. Known: {list(self.SOURCES)}")
        handler = getattr(self, f"_read_{self.SOURCES[source]}")
        return handler(**kwargs)

    def _read_kpi_definitions(self, **_kwargs) -> Dict[str, Any]:
        return copy.deepcopy(stub_data.KPI_DEFINITIONS)

    def _read_department_reports(self, domain: Optional[str] = None, **_kwargs) -> List[Dict[str, Any]]:
        if domain is None:
            raise ValueError("read('department reports', domain=...) requires a domain")
        self._require_access(domain)
        table = {
            "academic": stub_data.ACADEMIC_RECORDS,
            "research": stub_data.RESEARCH_RECORDS,
            "placement": stub_data.PLACEMENT_RECORDS,
            "finance": [stub_data.FINANCE_RECORD],
        }
        if domain not in table:
            raise ValueError(f"Unknown domain '{domain}'. Known: {list(table)}")
        return copy.deepcopy(table[domain])

    def _read_external_benchmarks(self, **_kwargs) -> Dict[str, Any]:
        # PLACEHOLDER: peer-institution / NIRF band benchmarks would live here.
        return {
            "nirf_band_placement_pct_median": 82.0,
            "nirf_band_publications_per_faculty_median": 1.0,
            "note": "illustrative placeholder benchmark, not a real NIRF publication",
        }

    def total_faculty_count(self) -> int:
        return stub_data.TOTAL_FACULTY_COUNT

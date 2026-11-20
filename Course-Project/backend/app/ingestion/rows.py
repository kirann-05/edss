"""The shape of what a source hands over, before anything is trusted.

A source system, whatever its columns are called, is read into RawRow values under the system's
own canonical column names. That is the whole contract between a source and the rest of the
system: change an adapter to read a new source, and nothing above it changes (the connector
principle, docs/ARCHITECTURE.md principle 4, docs/DATA_CONTRACT.md).
"""

from collections.abc import Mapping
from dataclasses import dataclass

FACT_REQUIRED = ("dept_code", "metric_key", "period_year", "period_sub", "value", "status", "as_of")
FACT_OPTIONAL = ("numerator", "denominator", "unit", "source_ref")
FACT_COLUMNS = (*FACT_REQUIRED, *FACT_OPTIONAL)

PUBLICATION_REQUIRED = ("dedup_key", "title", "period_year", "status", "dept_codes")
PUBLICATION_OPTIONAL = ("venue", "indexing")
PUBLICATION_COLUMNS = (*PUBLICATION_REQUIRED, *PUBLICATION_OPTIONAL)

DEPARTMENT_COLUMNS = ("code", "name", "school")


@dataclass(frozen=True)
class RawRow:
    """One record as the source gave it. `ref` says where it came from, so it can be found again."""

    ref: str
    values: Mapping[str, str | None]


class SchemaError(ValueError):
    """A source whose columns are wrong as a whole, which no row-by-row rejection could describe."""

    def __init__(self, source: str, missing: list[str]) -> None:
        super().__init__(
            f"{source} is missing the column{'s' if len(missing) != 1 else ''}: {', '.join(missing)}"
        )
        self.missing = missing

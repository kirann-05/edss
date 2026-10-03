"""The reconciliation report: what came in, what was refused and why, and where there is nothing.

This is what a data owner is shown to confirm or correct their extract (docs/BUILD_PLAN.md day 18).
It reports. It never fills a gap or corrects a figure.
"""

from collections import Counter
from datetime import date

from app.domain.enums import Domain
from app.ingestion.manifest import FolderResult

AREAS = (Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE)


def reconciliation_report(outcome: FolderResult, title: str, max_rejects: int = 60) -> str:
    ledger = outcome.ledger
    lines = [
        f"# Ingest report: {title}",
        "",
        f"Read on {ledger.today.isoformat()}. **{outcome.accepted} rows accepted, {outcome.rejected} rejected**"
        + (f", {len(outcome.errors)} file(s) could not be read." if outcome.errors else "."),
        "",
    ]
    if outcome.errors:
        lines += ["## Files that could not be read", ""] + [f"- {e}" for e in outcome.errors] + [""]

    lines += [
        "## Files",
        "",
        "| File | Source | Accepted | Rejected | Note |",
        "| --- | --- | --- | --- | --- |",
    ]
    sources = {s.id: s for s in ledger.sources}
    for label, result in outcome.results:
        note = "same content as before, nothing added" if result.noop else ""
        lines.append(
            f"| {label} | {sources[result.batch.source_system_id].name} | {result.accepted} | {len(result.rejects)} | {note} |"
        )

    if not ledger.facts:
        return "\n".join(lines) + "\n"

    period = max(f.period_year for f in ledger.facts)
    lines += [
        "",
        f"## Coverage for {period}",
        "",
        "A blank cell means no record. It is shown as missing, never as zero.",
        "",
    ]
    lines += [
        "| Department | " + " | ".join(d.value for d in AREAS) + " |",
        "| --- | " + " | ".join("---" for _ in AREAS) + " |",
    ]
    for department in ledger.departments:
        cells = []
        for domain in AREAS:
            facts = [
                f
                for f in ledger.facts
                if f.dept_code == department.code and f.domain is domain and f.period_year == period
            ]
            if not facts:
                cells.append("none")
                continue
            newest = max(f.as_of for f in facts)
            age = (ledger.today - newest).days
            cells.append(f"{len(facts)} records, newest {newest.isoformat()} ({age} days)")
        lines.append(f"| {department.code} | " + " | ".join(cells) + " |")

    mix = Counter((f.domain.value, f.status.value) for f in ledger.facts if f.period_year == period)
    odd = {k: n for k, n in mix.items() if k[1] not in ("final", "audited")}
    lines += ["", f"## Records that are not final, {period}", ""]
    lines += [
        f"- {domain}: {n} {status.replace('_', ' ')}" for (domain, status), n in sorted(odd.items())
    ] or ["- none"]

    rejects = [(label, r) for label, result in outcome.results for r in result.rejects]
    lines += ["", f"## Rejected rows ({len(rejects)})", ""]
    if rejects:
        lines += ["| Where | Why |", "| --- | --- |"]
        lines += [f"| {r.ref} | {'; '.join(r.reasons)} |" for _, r in rejects[:max_rejects]]
        if len(rejects) > max_rejects:
            lines.append(f"\n{len(rejects) - max_rejects} more not shown.")
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def today() -> date:
    return date.today()

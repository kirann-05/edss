"""Each planted trap, found again in a loaded store (docs/DATA_CONTRACT.md section 6).

The tests in tests/synthetic prove the system handles every trap. This answers a different
question, the one `make seed` asks after loading data anywhere (files now, Postgres later): is the
trap actually there to be handled? A seed that silently lost a trap would make every later test
pass for the wrong reason.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import FactStatus, KpiStatus
from app.services.store import DataStore
from app.synthetic.generator import SHARED_DOI


@dataclass(frozen=True)
class Trap:
    id: str
    what: str
    observed: str
    ok: bool


def observe(store: DataStore, stale_after_days: int = 90) -> list[Trap]:
    period = store.current_period
    results = store.results(period)
    current = store.facts(period)
    out: list[Trap] = []

    def trap(id_: str, what: str, observed: str, ok: bool) -> None:
        out.append(Trap(id_, what, observed, bool(ok)))

    pl = results["PL_PCT"]
    stale = pl.flags.stale_departments
    trap(
        "T1",
        "one department's placement data is older than the freshness window",
        f"stale: {', '.join(stale) or 'none'}",
        stale == ("CIVIL",),
    )

    missing = results["RS_PUB_PF"].flags.missing_departments
    trap(
        "T2",
        "one department has no research record for the latest year",
        f"missing: {', '.join(missing) or 'none'}",
        missing == ("MECH",),
    )

    confirmed = sum(f.value for f in current if f.metric_key == "plc.placed_confirmed")
    provisional = sum(f.value for f in current if f.metric_key == "plc.offers_provisional")
    share = provisional / (confirmed + provisional) if confirmed + provisional else Decimal(0)
    counted = {store.facts_by_id[i].metric_key for i in pl.input_fact_ids}
    trap(
        "T3",
        "about 12 percent of offers are provisional and never counted",
        f"{share * 100:.1f} percent provisional",
        Decimal("0.11") <= share <= Decimal("0.13") and "plc.offers_provisional" not in counted,
    )

    forecast = [f for f in current if f.metric_key == "fin.revenue_forecast"]
    summed = {store.facts_by_id[i].metric_key for i in results["FN_REV"].input_fact_ids}
    trap(
        "T4",
        "a forecast sits beside actual revenue and is never summed into it",
        f"{len(forecast)} forecast rows",
        bool(forecast)
        and all(f.status is FactStatus.FORECAST for f in forecast)
        and "fin.revenue_forecast" not in summed,
    )

    shared = [p for p in store.dataset.publications if p.dedup_key == SHARED_DOI]
    trap(
        "T5",
        "two departments share one DOI",
        f"{len(shared)} paper, credited to {', '.join(shared[0].dept_codes) if shared else 'nobody'}",
        len(shared) == 1 and set(shared[0].dept_codes) == {"CSE", "ECE"},
    )

    trap(
        "T6",
        "a KPI computes to 74.96 against a target of 75",
        f"{pl.value:.4f} against {pl.target}, {pl.status.value}",
        pl.value is not None
        and pl.value.quantize(Decimal("0.01")) == Decimal("74.96")
        and pl.status is KpiStatus.MISSED,
    )

    passing = results["AC_PASS_PCT"]
    rates = [v.value for v in passing.departments if v.value is not None]
    naive = sum(rates) / len(rates)
    trap(
        "T7",
        "the simple mean of department pass rates differs from the weighted rate",
        f"mean {naive:.2f} against weighted {passing.value:.2f}",
        passing.value is not None and abs(naive - passing.value) > Decimal(2),
    )

    pending = [f for f in store.dataset.facts if f.status is FactStatus.PENDING_RECONCILIATION]
    util = results["FN_UTIL"]
    trap(
        "T8",
        "one finance figure is pending reconciliation and kept out of actuals",
        f"{len(pending)} pending, excluded: {', '.join(util.flags.excluded_departments) or 'none'}",
        len(pending) == 1 and util.flags.excluded_departments == ("BIOTECH",),
    )

    undefined = pl.flags.undefined_departments
    trap(
        "T9",
        "one department has a zero denominator",
        f"undefined: {', '.join(undefined) or 'none'}",
        undefined == ("AIML",),
    )

    count = {s: sum(1 for r in results.values() if r.status is s) for s in KpiStatus}
    trap(
        "T10",
        "two KPIs miss, one is at risk, the rest are met",
        f"{count[KpiStatus.MISSED]} missed, {count[KpiStatus.AT_RISK]} at risk, {count[KpiStatus.MET]} met",
        (count[KpiStatus.MISSED], count[KpiStatus.AT_RISK], count[KpiStatus.MET]) == (2, 1, 10),
    )
    return out

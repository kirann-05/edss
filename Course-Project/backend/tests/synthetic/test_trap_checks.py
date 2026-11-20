"""The trap checker that `make seed` runs, and a proof that it can fail."""

from datetime import date

from app.domain.dataset import Dataset
from app.services.store import DataStore
from app.synthetic.traps import observe


def test_every_planted_trap_is_found_in_the_synthetic_store(store):
    traps = observe(store)
    assert [t.id for t in traps] == [f"T{n}" for n in range(1, 11)]
    assert [t.id for t in traps if not t.ok] == []


def test_each_check_says_what_it_saw(store):
    seen = {t.id: t.observed for t in observe(store)}
    assert (
        seen["T1"] == "stale: CIVIL"
        and seen["T2"] == "missing: MECH"
        and seen["T9"] == "undefined: AIML"
    )
    assert seen["T6"].endswith("missed") and "74.96" in seen["T6"]
    assert seen["T10"] == "2 missed, 1 at risk, 10 met"


def test_a_seed_that_lost_a_trap_is_caught(store):
    # remove the pending-reconciliation figure and the checker must notice T8 is gone
    from app.domain.enums import FactStatus

    facts = tuple(
        f for f in store.dataset.facts if f.status is not FactStatus.PENDING_RECONCILIATION
    )
    broken = DataStore(
        Dataset(**{**store.dataset.__dict__, "facts": facts}),
        list(store.definitions),
        [],
        date(2026, 10, 1),
        90,
    )
    broken_targets = store._target  # noqa: SLF001 - reuse the same targets
    broken._target = broken_targets  # noqa: SLF001
    failing = [t.id for t in observe(broken) if not t.ok]
    assert "T8" in failing

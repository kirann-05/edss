"""Rule 9: the audit log is append-only and hash-chained. Tampering is detectable (Lab 6)."""

import threading
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.governance.audit import GENESIS_HASH, AuditLog, canonical, compute_hash, verify_rows

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def log_with(n=5):
    log = AuditLog()
    for i in range(n):
        log.append(
            actor_type="agent",
            actor_id="academic",
            action="node.done",
            run_id="run-1",
            inputs={"step": i},
            outputs={"views": i * 2},
            ts=T0,
        )
    return log


class TestChain:
    def test_the_first_row_points_at_the_genesis_hash(self):
        assert log_with(1).rows()[0].prev_hash == GENESIS_HASH

    def test_each_row_points_at_the_hash_of_the_one_before(self):
        rows = log_with(5).rows()
        for before, after in zip(rows, rows[1:], strict=False):
            assert after.prev_hash == before.hash

    def test_ids_are_sequential_from_one(self):
        assert [r.id for r in log_with(4).rows()] == [1, 2, 3, 4]

    def test_an_intact_log_verifies(self):
        result = log_with(10).verify()
        assert result.ok and result.checked == 10 and result.broken_at is None

    def test_an_empty_log_verifies(self):
        assert AuditLog().verify().ok

    def test_the_hash_depends_on_everything_logged(self):
        base = dict(
            prev_hash=GENESIS_HASH,
            ts=T0,
            run_id="r",
            actor_type="user",
            actor_id="a",
            action="x",
            inputs={"k": 1},
            outputs={"v": 2},
        )
        reference = compute_hash(**base)
        for field, other in [
            ("ts", datetime(2026, 10, 3, 12, 0, 1, tzinfo=UTC)),
            ("run_id", "r2"),
            ("actor_type", "agent"),
            ("actor_id", "b"),
            ("action", "y"),
            ("inputs", {"k": 2}),
            ("outputs", {"v": 3}),
            ("prev_hash", "1" * 64),
        ]:
            assert compute_hash(**{**base, field: other}) != reference, field


class TestTamperDetection:
    @pytest.mark.parametrize(
        "change",
        [
            {"action": "node.failed"},
            {"actor_id": "someone-else"},
            {"inputs": {"step": 99}},
            {"outputs": {"views": 99}},
            {"run_id": "run-2"},
            {"ts": datetime(2027, 1, 1, tzinfo=UTC)},
        ],
    )
    def test_changing_any_logged_field_breaks_the_chain_at_that_row(self, change):
        rows = list(log_with(6).rows())
        rows[3] = replace(rows[3], **change)
        result = verify_rows(rows)
        assert not result.ok
        assert result.broken_at == rows[3].id

    def test_removing_a_row_is_detected_at_the_gap(self):
        rows = list(log_with(6).rows())
        del rows[2]
        result = verify_rows(rows)
        assert not result.ok and result.broken_at == 4  # the row after the gap no longer chains

    def test_reordering_rows_is_detected(self):
        rows = list(log_with(6).rows())
        rows[1], rows[2] = rows[2], rows[1]
        assert not verify_rows(rows).ok

    def test_a_forged_row_with_a_made_up_hash_is_detected(self):
        rows = list(log_with(3).rows())
        rows.append(replace(rows[-1], id=4, hash="f" * 64, prev_hash=rows[-1].hash))
        result = verify_rows(rows)
        assert not result.ok and result.broken_at == 4

    def test_rewriting_a_row_and_its_hash_still_breaks_the_next_row(self):
        rows = list(log_with(4).rows())
        forged = replace(rows[1], outputs={"views": 12345})
        rows[1] = replace(
            forged,
            hash=compute_hash(
                forged.prev_hash,
                forged.ts,
                forged.run_id,
                forged.actor_type,
                forged.actor_id,
                forged.action,
                forged.inputs,
                forged.outputs,
            ),
        )
        result = verify_rows(rows)
        assert not result.ok and result.broken_at == rows[2].id  # the chain remembers

    def test_the_log_hands_out_copies_so_a_caller_cannot_edit_history(self):
        log = log_with(3)
        log.rows().clear()
        assert len(log.rows()) == 3


class TestSingleWriter:
    """Decision D18: parallel nodes append at the same time and must not race on prev_hash."""

    def test_concurrent_writers_still_produce_one_valid_chain(self):
        log = AuditLog()

        def writer(name):
            for i in range(60):
                log.append(
                    actor_type="agent",
                    actor_id=name,
                    action="node.done",
                    run_id="r",
                    inputs={"i": i},
                )

        threads = [threading.Thread(target=writer, args=(f"agent-{n}",)) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        rows = log.rows()
        assert len(rows) == 480
        assert [r.id for r in rows] == list(range(1, 481))
        assert verify_rows(rows).ok


class TestCanonicalForm:
    def test_the_same_content_always_hashes_the_same_whatever_the_key_order(self):
        assert canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1})

    def test_decimals_dates_and_enums_have_a_stable_text_form(self):
        from app.domain.enums import KpiStatus

        text = canonical({"v": Decimal("74.96"), "d": date(2026, 10, 3), "s": KpiStatus.MISSED})
        assert text == '{"d":"2026-10-03","s":"missed","v":"74.96"}'

    def test_a_decimal_is_logged_as_text_never_a_float(self):
        assert "74.96" in canonical({"v": Decimal("74.96")})
        assert "74.9599999" not in canonical({"v": Decimal("74.96")})


class TestFiltering:
    def test_rows_can_be_filtered_by_run_actor_action_and_time(self):
        log = AuditLog()
        log.append(
            actor_type="user",
            actor_id="registrar@edss.test",
            action="plan.lock",
            run_id="r1",
            ts=T0,
        )
        log.append(actor_type="agent", actor_id="academic", action="node.done", run_id="r1", ts=T0)
        log.append(
            actor_type="agent",
            actor_id="finance",
            action="node.done",
            run_id="r2",
            ts=datetime(2026, 10, 4, tzinfo=UTC),
        )
        assert len(log.rows(run_id="r1")) == 2
        assert len(log.rows(actor_id="finance")) == 1
        assert len(log.rows(action="plan.lock")) == 1
        assert len(log.rows(since=datetime(2026, 10, 4, tzinfo=UTC))) == 1
        assert len(log.rows(until=datetime(2026, 10, 3, 23, tzinfo=UTC))) == 2

    def test_filtering_does_not_change_what_verify_checks(self):
        log = log_with(5)
        log.rows(run_id="nope")
        assert log.verify().checked == 5

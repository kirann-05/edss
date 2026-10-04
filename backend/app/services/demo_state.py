"""A demo that does not wait (docs/NEXT_STEPS.md D5).

With EDSS_DEMO_STATE on, the app starts with one approved report and one draft waiting for review,
so the Principal's part of the demo never waits on a run. Both are made through the real services:
the same planner, graph, validation gate and governance rules as a live run, under the synthetic
Registrar and Principal personas. The audit log says plainly, first, that this was seeded.

Only ever in demo mode, which needs synthetic data (deps.demo_login_enabled).
"""

import time

from app.api.deps import AppState
from app.governance.service import Decision
from app.services.runs import SETTLED, RunRecord

REPORT_REQUEST = "Governing Council brief for 2025-26 on everything"
DRAFT_REQUEST = "Placement and research brief for the Governing Council for 2025-26"


class DemoStateError(RuntimeError):
    pass


def _finish(state: AppState, record: RunRecord, timeout: float = 60.0) -> RunRecord:
    deadline = time.monotonic() + timeout
    while state.runs.get(record.id).status not in SETTLED:
        if time.monotonic() > deadline:
            raise DemoStateError(f"the seeded run {record.id} did not finish in {timeout:.0f} s")
        time.sleep(0.05)
    return state.runs.get(record.id)


def _draft(state: AppState, request: str) -> RunRecord:
    registrar = state.users.by_email("registrar@edss.test")
    assert registrar is not None
    record = state.runs.create(registrar, request)
    if record.questions:
        record = state.runs.skip_questions(registrar, record.id)
    # seeded while the server is starting, before it can answer its own connector endpoint
    state.runs.lock(registrar, record.id, [], reads_direct=True)
    done = _finish(state, record)
    if done.brief_id is None:
        raise DemoStateError(f"the seeded run {record.id} ended without a draft: {done.error}")
    return done


def seed_demo_state(state: AppState) -> dict[str, str]:
    state.audit.append(
        actor_type="system", actor_id="demo", action="demo.seed", inputs={},
        outputs={"note": "Demo state seeded at startup on synthetic data, under the Registrar and "
                 "Principal personas: one approved report and one draft waiting for review"},
    )  # fmt: skip
    principal = state.users.by_email("principal@edss.test")
    assert principal is not None

    report = _draft(state, REPORT_REQUEST)
    result = state.governance.decide(report.brief_id, principal, Decision(kind="approve"))  # type: ignore[arg-type]
    state.runs.on_decision(
        report.id, result.brief.status.value, result.brief.version, principal.name
    )
    _finish(state, report)

    waiting = _draft(state, DRAFT_REQUEST)
    return {"report_brief": report.brief_id or "", "waiting_brief": waiting.brief_id or ""}

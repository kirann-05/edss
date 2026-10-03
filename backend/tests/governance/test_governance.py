"""Lab 12: a named human approves, edits or overrides. Only approved content is published.

Rule 2: agents draft and flag, a named human approves. Nothing is published without an approval
record from an authorised role, and any release can be rolled back cleanly.
"""

import pytest

from app.agents.compose import compose_brief, off_target
from app.agents.llm import FakeLLM
from app.agents.models import CheckResult, Locator, ValidationReport, Violation
from app.agents.skills.options_skill import draft_option_set
from app.agents.validation.checks import ValidationContext
from app.agents.validation.suite import validate
from app.domain.enums import BriefStatus, Role
from app.domain.models import AppUser
from app.governance.audit import AuditLog
from app.governance.service import (
    Decision,
    EditRequest,
    GovernanceError,
    GovernanceService,
    PermissionDenied,
)


def person(role, name="Dr. Kavita Rao", **extra):
    return AppUser(id=1, email=f"{role.value}@edss.test", name=name, role=role, **extra)


PRINCIPAL = person(Role.PRINCIPAL)
REGISTRAR = person(Role.REGISTRAR, "Anand Deshpande")


@pytest.fixture(scope="module")
def vctx(store, connector, plan):
    return ValidationContext(
        plan=plan,
        facts=store.facts_by_id,
        sources=store.sources,
        publications=tuple(connector.get_publications(store.current_period)),
        definitions={d.key: d for d in store.definitions},
    )


@pytest.fixture(scope="module")
def clean(plan, figures, health):
    model = FakeLLM("drafter")
    return compose_brief(
        plan, figures, [draft_option_set(model, f) for f in off_target(figures)], health
    )


@pytest.fixture
def audit():
    return AuditLog()


@pytest.fixture
def gov(audit, vctx):
    return GovernanceService(audit, validator=lambda doc: validate(doc, vctx))


def draft(gov, clean, vctx, *, run="run-1", report=None, escalated=False):
    return gov.create_draft(
        run_id=run,
        document=clean,
        validation=report or validate(clean, vctx),
        attempts=1,
        escalated=escalated,
        diagnosis="needs a person" if escalated else None,
        repair_log=(),
        created_by="registrar@edss.test",
    )


def failing_report(*check_ids):
    checks = []
    for n in range(1, 10):
        cid = f"V{n}"
        bad = cid in check_ids
        violations = (
            (
                Violation(
                    locator=Locator(section="x"),
                    message=f"{cid} failed",
                    diagnosis=f"{cid} diagnosis",
                ),
            )
            if bad
            else ()
        )
        checks.append(CheckResult(id=cid, name=cid, passed=not bad, violations=violations))
    return ValidationReport(passed=not check_ids, checks=tuple(checks), attempt=3)


class TestApprove:
    def test_an_authorised_approver_publishes_the_first_version(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        result = gov.decide(brief.id, PRINCIPAL, Decision(kind="approve"))
        assert result.brief.status is BriefStatus.PUBLISHED
        assert result.version.version == 1
        assert gov.current().version == 1
        assert result.version.approved_by == "Dr. Kavita Rao"

    @pytest.mark.parametrize("role", [Role.DEAN, Role.HOD, Role.VIEWER, Role.ADMIN])
    def test_nobody_without_the_approve_permission_can_approve(self, gov, clean, vctx, role):
        user = person(
            role,
            dept_code="CSE" if role is Role.HOD else None,
            school="S" if role is Role.DEAN else None,
        )
        brief = draft(gov, clean, vctx)
        with pytest.raises(PermissionDenied):
            gov.decide(brief.id, user, Decision(kind="approve"))
        assert gov.current() is None  # nothing was published
        assert gov.get(brief.id).status is BriefStatus.DRAFT

    def test_a_brief_can_only_be_decided_once(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        gov.decide(brief.id, PRINCIPAL, Decision(kind="approve"))
        with pytest.raises(GovernanceError, match="already"):
            gov.decide(brief.id, PRINCIPAL, Decision(kind="approve"))

    def test_there_is_no_way_to_publish_that_skips_the_decision(self, gov):
        # rule 2: publishing is only ever the result of an approval by an authorised role
        public = {name for name in dir(gov) if not name.startswith("_")}
        assert not {name for name in public if "publish" in name}

    def test_a_draft_that_did_not_pass_validation_cannot_be_approved(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx, report=failing_report("V3"))
        with pytest.raises(GovernanceError, match="validation"):
            gov.decide(brief.id, PRINCIPAL, Decision(kind="approve"))


class TestEscalated:
    """Decision D13: an escalated draft reaches a person, but cannot be approved past an
    integrity failure."""

    @pytest.mark.parametrize("check", ["V1", "V4", "V5", "V6", "V7", "V9"])
    def test_an_integrity_failure_blocks_approval_even_when_acknowledged(
        self, gov, clean, vctx, check
    ):
        brief = draft(gov, clean, vctx, report=failing_report(check), escalated=True)
        with pytest.raises(GovernanceError, match="integrity"):
            gov.decide(brief.id, PRINCIPAL, Decision(kind="approve", ack_escalation=True))
        assert gov.current() is None

    @pytest.mark.parametrize("check", ["V2", "V3", "V8"])
    def test_a_completeness_failure_can_be_approved_only_with_an_acknowledgement(
        self, gov, clean, vctx, check
    ):
        brief = draft(gov, clean, vctx, report=failing_report(check), escalated=True)
        with pytest.raises(GovernanceError, match="acknowledge"):
            gov.decide(brief.id, PRINCIPAL, Decision(kind="approve"))
        result = gov.decide(brief.id, PRINCIPAL, Decision(kind="approve", ack_escalation=True))
        assert result.brief.status is BriefStatus.PUBLISHED
        assert result.version.escalation_acknowledged is True

    def test_an_integrity_failure_can_still_be_overridden_or_sent_back(self, gov, clean, vctx):
        a = draft(gov, clean, vctx, run="r1", report=failing_report("V1"), escalated=True)
        gov.decide(a.id, PRINCIPAL, Decision(kind="override", reason="Not safe to publish"))
        b = draft(gov, clean, vctx, run="r2", report=failing_report("V1"), escalated=True)
        gov.decide(b.id, PRINCIPAL, Decision(kind="send_back", reason="Redo the research section"))
        assert gov.get(a.id).status is BriefStatus.OVERRIDDEN
        assert gov.get(b.id).status is BriefStatus.RETURNED


class TestEdit:
    def test_an_edit_is_applied_revalidated_and_recorded_as_a_diff(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        option = clean.option_sets[0].options[0]
        new_text = "Concentrate support where the figure is weakest, and review it each cycle."
        result = gov.decide(
            brief.id,
            PRINCIPAL,
            Decision(
                kind="edit",
                edits=(EditRequest(option_id=option.id, field="description", value=new_text),),
            ),
        )
        assert result.brief.status is BriefStatus.PUBLISHED
        edited = next(
            o for s in result.version.document.option_sets for o in s.options if o.id == option.id
        )
        assert edited.description == new_text
        (edit,) = result.version.edits
        assert (edit.option_id, edit.field) == (option.id, "description")
        assert edit.before == option.description and edit.after == new_text
        assert edit.by == "Dr. Kavita Rao"

    def test_an_edit_that_writes_a_figure_by_hand_is_refused_and_nothing_is_published(
        self, gov, clean, vctx
    ):
        brief = draft(gov, clean, vctx)
        option = clean.option_sets[0].options[0]
        with pytest.raises(GovernanceError, match="validation") as caught:
            gov.decide(
                brief.id,
                PRINCIPAL,
                Decision(
                    kind="edit",
                    edits=(
                        EditRequest(
                            option_id=option.id, field="description", value="Raise it by 12%."
                        ),
                    ),
                ),
            )
        assert caught.value.report is not None and not caught.value.report.passed
        assert gov.current() is None
        assert gov.get(brief.id).status is BriefStatus.DRAFT  # still waiting for a decision

    def test_an_edit_can_replace_a_list_field(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        option = clean.option_sets[0].options[0]
        result = gov.decide(
            brief.id,
            PRINCIPAL,
            Decision(
                kind="edit",
                edits=(
                    EditRequest(
                        option_id=option.id, field="risks", value=["A new risk the approver added."]
                    ),
                ),
            ),
        )
        edited = next(
            o for s in result.version.document.option_sets for o in s.options if o.id == option.id
        )
        assert edited.risks == ("A new risk the approver added.",)

    def test_an_unknown_option_is_refused(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        with pytest.raises(GovernanceError, match="no option"):
            gov.decide(
                brief.id,
                PRINCIPAL,
                Decision(
                    kind="edit",
                    edits=(EditRequest(option_id="NOPE-9", field="description", value="x"),),
                ),
            )

    def test_an_edit_with_no_changes_is_refused(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        with pytest.raises(GovernanceError, match="at least one"):
            gov.decide(brief.id, PRINCIPAL, Decision(kind="edit"))


class TestOverrideAndSendBack:
    def test_an_override_needs_a_reason_and_publishes_nothing(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        with pytest.raises(GovernanceError, match="reason"):
            gov.decide(brief.id, PRINCIPAL, Decision(kind="override"))
        gov.decide(
            brief.id, PRINCIPAL, Decision(kind="override", reason="Council meeting postponed")
        )
        assert gov.get(brief.id).status is BriefStatus.OVERRIDDEN
        assert gov.current() is None

    def test_sending_back_needs_a_reason(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        with pytest.raises(GovernanceError, match="reason"):
            gov.decide(brief.id, PRINCIPAL, Decision(kind="send_back", reason="  "))

    def test_an_unknown_brief_is_a_clear_error(self, gov):
        with pytest.raises(GovernanceError, match="no brief"):
            gov.decide("nope", PRINCIPAL, Decision(kind="approve"))


class TestVersionsAndRollback:
    def publish_two(self, gov, clean, vctx):
        a = gov.decide(draft(gov, clean, vctx, run="r1").id, PRINCIPAL, Decision(kind="approve"))
        b = gov.decide(draft(gov, clean, vctx, run="r2").id, REGISTRAR, Decision(kind="approve"))
        return a.version, b.version

    def test_versions_increase_and_the_pointer_follows_the_newest(self, gov, clean, vctx):
        v1, v2 = self.publish_two(gov, clean, vctx)
        assert (v1.version, v2.version) == (1, 2)
        assert gov.current().version == 2
        assert [v.version for v in gov.versions()] == [1, 2]

    def test_rollback_moves_the_pointer_and_never_edits_history(self, gov, clean, vctx, audit):
        v1, v2 = self.publish_two(gov, clean, vctx)
        before = [v.document.model_dump_json() for v in gov.versions()]
        gov.rollback(PRINCIPAL, to_version=1, reason="Version two used a stale placement figure")
        assert gov.current().version == 1
        assert [v.document.model_dump_json() for v in gov.versions()] == before  # history untouched
        states = {v.version: gov.state_of(v.version) for v in gov.versions()}
        assert states == {1: "current", 2: "rolled_back"}
        assert gov.get(v2.brief_id).status is BriefStatus.ROLLED_BACK
        assert audit.verify().ok

    def test_a_new_publication_after_a_rollback_continues_the_numbering(self, gov, clean, vctx):
        self.publish_two(gov, clean, vctx)
        gov.rollback(PRINCIPAL, to_version=1, reason="Back to the good one")
        v3 = gov.decide(
            draft(gov, clean, vctx, run="r3").id, PRINCIPAL, Decision(kind="approve")
        ).version
        assert v3.version == 3 and gov.current().version == 3

    def test_rollback_needs_the_permission_and_a_reason(self, gov, clean, vctx):
        self.publish_two(gov, clean, vctx)
        with pytest.raises(PermissionDenied):
            gov.rollback(person(Role.DEAN, school="S"), to_version=1, reason="x")
        with pytest.raises(GovernanceError, match="reason"):
            gov.rollback(PRINCIPAL, to_version=1, reason="")
        assert gov.current().version == 2

    @pytest.mark.parametrize("target", [2, 9])
    def test_rolling_back_to_the_current_or_an_unknown_version_is_refused(
        self, gov, clean, vctx, target
    ):
        self.publish_two(gov, clean, vctx)
        with pytest.raises(GovernanceError):
            gov.rollback(PRINCIPAL, to_version=target, reason="no")

    def test_a_published_version_is_a_frozen_snapshot(self, gov, clean, vctx):
        v1, _ = self.publish_two(gov, clean, vctx)
        with pytest.raises(Exception):  # noqa: B017  (any attempt to change a frozen record fails)
            v1.document.title = "tampered"  # type: ignore[misc]


class TestDiff:
    def test_a_diff_lists_changed_options_and_figures(self, gov, clean, vctx):
        a = gov.decide(
            draft(gov, clean, vctx, run="r1").id, PRINCIPAL, Decision(kind="approve")
        ).version
        option = clean.option_sets[0].options[0]
        b = gov.decide(
            draft(gov, clean, vctx, run="r2").id,
            PRINCIPAL,
            Decision(
                kind="edit",
                edits=(EditRequest(option_id=option.id, field="title", value="A different title"),),
            ),
        ).version
        changes = gov.diff(a.version, b.version)
        assert [(c.section, c.option_id, c.kind) for c in changes] == [
            ("options", option.id, "changed")
        ]
        assert changes[0].before == option.title and changes[0].after == "A different title"

    def test_identical_versions_have_no_diff(self, gov, clean, vctx):
        a = gov.decide(
            draft(gov, clean, vctx, run="r1").id, PRINCIPAL, Decision(kind="approve")
        ).version
        b = gov.decide(
            draft(gov, clean, vctx, run="r2").id, PRINCIPAL, Decision(kind="approve")
        ).version
        assert gov.diff(a.version, b.version) == []


class TestAudit:
    def test_every_decision_is_an_audit_row_naming_the_person_and_the_reason(
        self, gov, clean, vctx, audit
    ):
        brief = draft(gov, clean, vctx)
        gov.decide(brief.id, PRINCIPAL, Decision(kind="override", reason="Postponed"))
        row = audit.rows(action="brief.override")[0]
        assert row.actor_type == "user" and row.actor_id == "principal@edss.test"
        assert row.outputs["reason"] == "Postponed"
        assert audit.verify().ok

    def test_a_refused_attempt_is_logged_too(self, gov, clean, vctx, audit):
        brief = draft(gov, clean, vctx)
        with pytest.raises(PermissionDenied):
            gov.decide(brief.id, person(Role.VIEWER), Decision(kind="approve"))
        assert audit.rows(action="brief.refused")


class TestApprovalState:
    """The UI asks the server whether Approve is allowed, so the rule lives in one place."""

    def test_a_passing_draft_can_be_approved(self, gov, clean, vctx):
        state = gov.approval_state(draft(gov, clean, vctx).id)
        assert (
            state.can_approve and not state.needs_acknowledgement and state.blocked_reason is None
        )

    def test_an_escalated_draft_failing_only_completeness_needs_an_acknowledgement(
        self, gov, clean, vctx
    ):
        brief = draft(gov, clean, vctx, report=failing_report("V3"), escalated=True)
        state = gov.approval_state(brief.id)
        assert state.can_approve and state.needs_acknowledgement and state.failing_checks == ["V3"]

    def test_an_escalated_draft_failing_integrity_cannot_be_approved_and_says_why(
        self, gov, clean, vctx
    ):
        brief = draft(gov, clean, vctx, report=failing_report("V1", "V3"), escalated=True)
        state = gov.approval_state(brief.id)
        assert not state.can_approve and "V1" in state.blocked_reason

    def test_a_decided_brief_cannot_be_approved_again(self, gov, clean, vctx):
        brief = draft(gov, clean, vctx)
        gov.decide(brief.id, PRINCIPAL, Decision(kind="approve"))
        assert not gov.approval_state(brief.id).can_approve

    def test_the_state_always_agrees_with_what_decide_actually_does(self, gov, clean, vctx):
        for checks, escalated in [
            ((), False),
            (("V3",), True),
            (("V1",), True),
            (("V2", "V8"), True),
        ]:
            brief = draft(
                gov,
                clean,
                vctx,
                run=f"r-{checks}",
                report=failing_report(*checks),
                escalated=escalated,
            )
            state = gov.approval_state(brief.id)
            try:
                gov.decide(brief.id, PRINCIPAL, Decision(kind="approve", ack_escalation=True))
                allowed = True
            except GovernanceError:
                allowed = False
            assert allowed == state.can_approve, checks

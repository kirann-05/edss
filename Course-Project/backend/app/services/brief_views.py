"""Turns stored briefs and versions into API responses.

A brief reaches the UI already rendered. Every figure in its text is a segment that carries its
display text and status, so the UI never parses a token, formats a number or decides a status.
"""

from collections.abc import Sequence

from app.agents.connector import Connector
from app.agents.models import BriefDocument, KpiFigure
from app.agents.tokens import render_segments
from app.agents.validation.checks import ValidationContext, render_context
from app.api import schemas as s
from app.core.rbac import Permission, Scope, has_permission
from app.domain.enums import KpiStatus
from app.domain.models import AppUser
from app.governance.service import ApprovalState, BriefRecord, BriefVersion, Edit
from app.services.views import _flag_list
from app.specialists import SPECIALISTS

_EVERYTHING = Scope(everything=True)


def figure_out(f: KpiFigure) -> s.FigureOut:
    flags = f.flags
    return s.FigureOut(
        key=f.key,
        name=f.name,
        domain=f.domain,
        unit=f.unit,
        precision=f.precision,
        higher_is_better=f.higher_is_better,
        placeholder=f.placeholder,
        value=f.value,
        target=f.target,
        variance_abs=f.variance_abs,
        status=f.status,
        as_of=f.as_of,
        flags=s.KpiFlagsOut(
            stale=_flag_list(flags.stale_departments, _EVERYTHING),
            missing=_flag_list(flags.missing_departments, _EVERYTHING),
            excluded=_flag_list(flags.excluded_departments, _EVERYTHING),
            undefined=_flag_list(flags.undefined_departments, _EVERYTHING),
            excluded_fact_count=len(flags.excluded_fact_ids),
            no_target=flags.no_target,
        ),
        input_fact_count=len(f.input_fact_ids),
        trend=f.trend,
    )


def render_document(doc: BriefDocument, ctx: ValidationContext) -> s.BriefDocumentOut:
    rc = render_context(doc, ctx)

    def rich(text: str) -> s.RichTextOut:
        return s.RichTextOut(text=text, segments=render_segments(text, rc))

    names = {k.key: k for k in doc.kpis}
    return s.BriefDocumentOut(
        title=doc.title,
        period_year=doc.period_year,
        kpis=[figure_out(k) for k in doc.kpis],
        summary=[
            s.SummaryOut(kpi_key=item.kpi_key, text=rich(item.headline)) for item in doc.summary
        ],
        option_sets=[
            s.OptionSetOut(
                kpi_key=option_set.kpi_key,
                kpi_name=names[option_set.kpi_key].name
                if option_set.kpi_key in names
                else option_set.kpi_key,
                status=names[option_set.kpi_key].status
                if option_set.kpi_key in names
                else KpiStatus.UNDEFINED,
                attempt=option_set.attempt,
                guided_by=SPECIALISTS.get(option_set.framework).label,
                options=[
                    s.OptionOut(
                        id=o.id,
                        title=o.title,
                        description=rich(o.description),
                        assumptions=[rich(x) for x in o.assumptions],
                        risks=[rich(x) for x in o.risks],
                        trade_offs=[rich(x) for x in o.trade_offs],
                    )
                    for o in option_set.options
                ],
            )
            for option_set in doc.option_sets
        ],
        assumptions=[
            s.AssumptionOut(
                kind=a.kind, dept_code=a.dept_code, kpi_keys=list(a.kpi_keys), text=rich(a.text)
            )
            for a in doc.assumptions
        ],
        data_health=[
            s.HealthNoteOut(
                dept_code=n.dept_code,
                domain=n.domain,
                state=n.state,
                as_of=n.as_of,
                non_final=list(n.non_final),
            )
            for n in doc.data_health
        ],
    )


def _edit_out(e: Edit) -> s.EditOut:
    return s.EditOut(
        option_id=e.option_id, field=e.field, before=e.before, after=e.after, by=e.by, at=e.at
    )


def _off_target(doc: BriefDocument) -> int:
    return sum(1 for k in doc.kpis if k.status in (KpiStatus.MISSED, KpiStatus.AT_RISK))


def brief_out(
    record: BriefRecord,
    request: str | None,
    approval: ApprovalState,
    user: AppUser,
    ctx: ValidationContext,
) -> s.BriefOut:
    return s.BriefOut(
        id=record.id,
        run_id=record.run_id,
        status=record.status,
        escalated=record.escalated,
        diagnosis=record.diagnosis,
        attempts=record.attempts,
        created_at=record.created_at,
        created_by=record.created_by,
        request=request,
        period_year=record.document.period_year,
        document=render_document(record.document, ctx),
        validation=record.validation,
        history=list(record.history),
        repair_log=list(record.repair_log),
        approval=(
            s.ApprovalOut(
                actor_name=record.approval.actor_name,
                role=record.approval.role,
                at=record.approval.at,
                ack_escalation=record.approval.ack_escalation,
            )
            if record.approval
            else None
        ),
        edits=[_edit_out(e) for e in record.edits],
        version=record.version,
        decision_reason=record.decision_reason,
        approval_state=s.ApprovalStateOut(
            can_approve=approval.can_approve,
            blocked_reason=approval.blocked_reason,
            needs_acknowledgement=approval.needs_acknowledgement,
            failing_checks=list(approval.failing_checks),
        ),
        can_decide=has_permission(user, Permission.APPROVE),
    )


def brief_summary(record: BriefRecord, request: str | None) -> s.BriefSummaryOut:
    return s.BriefSummaryOut(
        id=record.id,
        run_id=record.run_id,
        status=record.status,
        escalated=record.escalated,
        validation_passed=record.validation.passed,
        failing_checks=[c.id for c in record.validation.failing],
        attempts=record.attempts,
        created_at=record.created_at,
        request=request,
        period_year=record.document.period_year,
        off_target_count=_off_target(record.document),
    )


def version_out(version: BriefVersion, state: str) -> s.VersionOut:
    return s.VersionOut(
        version=version.version,
        brief_id=version.brief_id,
        run_id=version.run_id,
        title=version.document.title,
        period_year=version.document.period_year,
        approved_by=version.approved_by,
        approved_at=version.approved_at,
        state=state,  # type: ignore[arg-type]
        escalation_acknowledged=version.escalation_acknowledged,
        edit_count=len(version.edits),
        kpi_count=len(version.document.kpis),
    )


def version_detail(version: BriefVersion, state: str, ctx: ValidationContext) -> s.VersionDetailOut:
    return s.VersionDetailOut(
        **version_out(version, state).model_dump(),
        document=render_document(version.document, ctx),
        edits=[_edit_out(e) for e in version.edits],
    )


def evidence_rows(doc: BriefDocument, connector: Connector) -> list[s.EvidenceRowOut]:
    """Lab 9: for every claim in the brief, the records it rests on and where they came from."""
    rows = []
    for figure in doc.kpis:
        systems: set[str] = set()
        for fact_id in figure.input_fact_ids:
            fact = connector.get_fact(fact_id)
            source = connector.get_source(fact.source_system_id) if fact else None
            if source:
                systems.add(source.name)
        count = len(figure.included_departments)
        rows.append(
            s.EvidenceRowOut(
                kpi_key=figure.key,
                claim=figure.name,
                fact_ids=list(figure.input_fact_ids),
                source_systems=sorted(systems),
                scope=f"{figure.period_year}, {count} department{'s' if count != 1 else ''}: "
                f"{', '.join(figure.included_departments) or 'none'}",
                tags=[
                    figure.domain.value,
                    figure.status.value,
                    *(["placeholder"] if figure.placeholder else []),
                ],
            )
        )
    return rows


def kpi_names(figures: Sequence[KpiFigure]) -> dict[str, str]:
    return {f.key: f.name for f in figures}

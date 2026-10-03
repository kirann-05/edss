from fastapi import APIRouter, Depends, HTTPException, status

from app.api import schemas as s
from app.api.deps import Period, State, require, scope_of
from app.core.rbac import Permission
from app.domain.enums import Domain
from app.domain.models import AppUser
from app.services import views
from app.services.store import UnknownKpiError

router = APIRouter(tags=["kpis"])
Viewer = Depends(require(Permission.VIEW_DASHBOARD))


@router.get("/kpis", response_model=s.KpiListOut)
def list_kpis(state: State, period: Period, user: AppUser = Viewer) -> s.KpiListOut:
    return views.build_kpi_list(state.store, scope_of(user, state), period)


@router.get("/kpis/{key}", response_model=s.KpiDrilldownOut)
def drilldown(key: str, state: State, period: Period, user: AppUser = Viewer) -> s.KpiDrilldownOut:
    try:
        return views.build_drilldown(state.store, scope_of(user, state), key, period)
    except UnknownKpiError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown KPI {key!r}") from None


@router.get("/domains/{domain}", response_model=s.DomainViewOut)
def domain_view(
    domain: Domain, state: State, period: Period, user: AppUser = Viewer
) -> s.DomainViewOut:
    if domain is Domain.REFERENCE:  # denominators only, not a tab of its own
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown domain")
    return views.build_domain_view(state.store, scope_of(user, state), domain, period)

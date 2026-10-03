from fastapi import APIRouter, Depends

from app.api import schemas as s
from app.api.deps import Period, State, require, scope_of
from app.core.rbac import Permission
from app.domain.models import AppUser
from app.services import views

router = APIRouter(tags=["data health"])
Reader = Depends(require(Permission.VIEW_DATA_HEALTH))


@router.get("/data-health", response_model=s.DataHealthOut)
def data_health(state: State, period: Period, user: AppUser = Reader) -> s.DataHealthOut:
    return views.build_data_health(state.store, scope_of(user, state), period)

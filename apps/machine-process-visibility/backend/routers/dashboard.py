from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from auth import require_admin, require_ready_user
from dashboard_service import list_workload


router = APIRouter(prefix="/api/dashboard")


@router.get("/workload")
def workload(
    period: str = Query("month"),
    base_date: Optional[str] = Query(None),
    user: dict[str, Any] = Depends(require_ready_user),
) -> dict[str, Any]:
    require_admin(user)
    return list_workload(period=period, base_date=base_date)

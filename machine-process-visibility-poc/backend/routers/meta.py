from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from auth import require_ready_user
from constants import COMMENT_TYPES
from database import db


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta")
def meta(user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    with db() as conn:
        return {
            "processes": [dict(row) for row in conn.execute("SELECT * FROM processes ORDER BY sort_order")],
            "assignees": [dict(row) for row in conn.execute("SELECT * FROM assignees WHERE active = 1 ORDER BY id")],
            "tags": [dict(row) for row in conn.execute("SELECT * FROM tags ORDER BY id")],
            "comment_types": sorted(COMMENT_TYPES),
        }

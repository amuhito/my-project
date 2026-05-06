from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from admin_service import (
    create_tag_for_admin,
    delete_tag_for_admin,
    list_admin_assignees,
    list_admin_tags,
    list_admin_users,
    reset_password_for_user,
    update_assignee_active_status,
    update_assignee_detail,
    update_tag_detail,
    update_user_active_status,
)
from auth import require_admin, require_ready_user
from schemas import ActivePayload, AssigneePayload, TagPayload


router = APIRouter(prefix="/api/admin")


def admin_user(user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    require_admin(user)
    return user


@router.get("/users")
def list_users(user: dict[str, Any] = Depends(admin_user)) -> list[dict[str, Any]]:
    return list_admin_users()


@router.put("/users/{user_id}/active")
def update_user_active(user_id: int, payload: ActivePayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    return update_user_active_status(user_id, payload, user)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: int, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    return reset_password_for_user(user_id)


@router.get("/assignees")
def list_assignees(user: dict[str, Any] = Depends(admin_user)) -> list[dict[str, Any]]:
    return list_admin_assignees()


@router.put("/assignees/{assignee_id}")
def update_assignee(assignee_id: int, payload: AssigneePayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    return update_assignee_detail(assignee_id, payload)


@router.put("/assignees/{assignee_id}/active")
def update_assignee_active(assignee_id: int, payload: ActivePayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    return update_assignee_active_status(assignee_id, payload)


@router.get("/tags")
def list_tags(user: dict[str, Any] = Depends(admin_user)) -> list[dict[str, Any]]:
    return list_admin_tags()


@router.post("/tags")
def create_tag(payload: TagPayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    return create_tag_for_admin(payload)


@router.put("/tags/{tag_id}")
def update_tag(tag_id: int, payload: TagPayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    return update_tag_detail(tag_id, payload)


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, user: dict[str, Any] = Depends(admin_user)) -> dict[str, str]:
    return delete_tag_for_admin(tag_id)

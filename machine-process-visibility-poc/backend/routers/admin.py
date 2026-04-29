from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from auth import hash_password, require_admin, require_ready_user
from database import db, row_to_dict
from schemas import ActivePayload, AssigneePayload, TagPayload
from utils import now_iso


router = APIRouter(prefix="/api/admin")


def admin_user(user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    require_admin(user)
    return user


@router.get("/users")
def list_users(user: dict[str, Any] = Depends(admin_user)) -> list[dict[str, Any]]:
    with db() as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT users.id, users.username, users.display_name, users.assignee_id, users.role,
                       users.active, users.password_must_change, users.password_changed_at,
                       users.created_at, assignees.name AS assignee_name
                FROM users
                LEFT JOIN assignees ON assignees.id = users.assignee_id
                ORDER BY users.id
                """
            ).fetchall()
        ]


@router.put("/users/{user_id}/active")
def update_user_active(user_id: int, payload: ActivePayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    if user_id == user["id"] and not payload.active:
        raise HTTPException(status_code=400, detail="自分自身は無効化できません")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if payload.active else 0, user_id))
        if not payload.active:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        return dict(conn.execute("SELECT id, username, display_name, role, active FROM users WHERE id = ?", (user_id,)).fetchone())


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: int, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    temporary_password = secrets.token_urlsafe(9)
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?, password_must_change = 1, password_changed_at = NULL
            WHERE id = ?
            """,
            (hash_password(temporary_password), user_id),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        return {"temporary_password": temporary_password}


@router.get("/assignees")
def list_assignees(user: dict[str, Any] = Depends(admin_user)) -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM assignees ORDER BY id").fetchall()]


@router.put("/assignees/{assignee_id}")
def update_assignee(assignee_id: int, payload: AssigneePayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute("SELECT 1 FROM assignees WHERE id = ?", (assignee_id,)).fetchone():
            raise HTTPException(status_code=404, detail="担当者が見つかりません")
        conn.execute(
            "UPDATE assignees SET name = ?, color = ?, active = ? WHERE id = ?",
            (payload.name.strip(), payload.color.strip(), 1 if payload.active else 0, assignee_id),
        )
        return dict(conn.execute("SELECT * FROM assignees WHERE id = ?", (assignee_id,)).fetchone())


@router.put("/assignees/{assignee_id}/active")
def update_assignee_active(assignee_id: int, payload: ActivePayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute("SELECT 1 FROM assignees WHERE id = ?", (assignee_id,)).fetchone():
            raise HTTPException(status_code=404, detail="担当者が見つかりません")
        conn.execute("UPDATE assignees SET active = ? WHERE id = ?", (1 if payload.active else 0, assignee_id))
        return dict(conn.execute("SELECT * FROM assignees WHERE id = ?", (assignee_id,)).fetchone())


@router.get("/tags")
def list_tags(user: dict[str, Any] = Depends(admin_user)) -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM tags ORDER BY id").fetchall()]


@router.post("/tags")
def create_tag(payload: TagPayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    with db() as conn:
        cur = conn.execute("INSERT INTO tags(name, color) VALUES (?, ?)", (payload.name.strip(), payload.color.strip()))
        return dict(conn.execute("SELECT * FROM tags WHERE id = ?", (cur.lastrowid,)).fetchone())


@router.put("/tags/{tag_id}")
def update_tag(tag_id: int, payload: TagPayload, user: dict[str, Any] = Depends(admin_user)) -> dict[str, Any]:
    with db() as conn:
        if not row_to_dict(conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()):
            raise HTTPException(status_code=404, detail="タグが見つかりません")
        conn.execute("UPDATE tags SET name = ?, color = ? WHERE id = ?", (payload.name.strip(), payload.color.strip(), tag_id))
        return dict(conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone())


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, user: dict[str, Any] = Depends(admin_user)) -> dict[str, str]:
    with db() as conn:
        if not conn.execute("SELECT 1 FROM tags WHERE id = ?", (tag_id,)).fetchone():
            raise HTTPException(status_code=404, detail="タグが見つかりません")
        conn.execute("DELETE FROM card_tags WHERE tag_id = ?", (tag_id,))
        conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        return {"status": "ok"}

from __future__ import annotations

import secrets
from typing import Any

from fastapi import HTTPException

from auth import hash_password
from database import db, row_to_dict
from schemas import ActivePayload, AssigneePayload, TagPayload


def list_admin_users() -> list[dict[str, Any]]:
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


def update_user_active_status(user_id: int, payload: ActivePayload, current_user: dict[str, Any]) -> dict[str, Any]:
    if user_id == current_user["id"] and not payload.active:
        raise HTTPException(status_code=400, detail="自分自身は無効化できません")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if payload.active else 0, user_id))
        if not payload.active:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        return dict(conn.execute("SELECT id, username, display_name, role, active FROM users WHERE id = ?", (user_id,)).fetchone())


def reset_password_for_user(user_id: int) -> dict[str, Any]:
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


def list_admin_assignees() -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM assignees ORDER BY id").fetchall()]


def update_assignee_detail(assignee_id: int, payload: AssigneePayload) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute("SELECT 1 FROM assignees WHERE id = ?", (assignee_id,)).fetchone():
            raise HTTPException(status_code=404, detail="担当者が見つかりません")
        conn.execute(
            "UPDATE assignees SET name = ?, color = ?, active = ? WHERE id = ?",
            (payload.name.strip(), payload.color.strip(), 1 if payload.active else 0, assignee_id),
        )
        return dict(conn.execute("SELECT * FROM assignees WHERE id = ?", (assignee_id,)).fetchone())


def update_assignee_active_status(assignee_id: int, payload: ActivePayload) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute("SELECT 1 FROM assignees WHERE id = ?", (assignee_id,)).fetchone():
            raise HTTPException(status_code=404, detail="担当者が見つかりません")
        conn.execute("UPDATE assignees SET active = ? WHERE id = ?", (1 if payload.active else 0, assignee_id))
        return dict(conn.execute("SELECT * FROM assignees WHERE id = ?", (assignee_id,)).fetchone())


def list_admin_tags() -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM tags ORDER BY id").fetchall()]


def create_tag_for_admin(payload: TagPayload) -> dict[str, Any]:
    with db() as conn:
        cur = conn.execute("INSERT INTO tags(name, color) VALUES (?, ?)", (payload.name.strip(), payload.color.strip()))
        return dict(conn.execute("SELECT * FROM tags WHERE id = ?", (cur.lastrowid,)).fetchone())


def update_tag_detail(tag_id: int, payload: TagPayload) -> dict[str, Any]:
    with db() as conn:
        if not row_to_dict(conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()):
            raise HTTPException(status_code=404, detail="タグが見つかりません")
        conn.execute("UPDATE tags SET name = ?, color = ? WHERE id = ?", (payload.name.strip(), payload.color.strip(), tag_id))
        return dict(conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone())


def delete_tag_for_admin(tag_id: int) -> dict[str, str]:
    with db() as conn:
        if not conn.execute("SELECT 1 FROM tags WHERE id = ?", (tag_id,)).fetchone():
            raise HTTPException(status_code=404, detail="タグが見つかりません")
        conn.execute("DELETE FROM card_tags WHERE tag_id = ?", (tag_id,))
        conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        return {"status": "ok"}

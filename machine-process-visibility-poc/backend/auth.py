from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import bcrypt
import sqlite3
from fastapi import Depends, Header, HTTPException

from constants import SESSION_HOURS
from database import db, row_to_dict
from utils import now_iso


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def legacy_hash_password(password: str) -> str:
    import hashlib

    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    return legacy_hash_password(password) == stored_hash


def session_expiry_iso() -> str:
    from datetime import timedelta

    return (datetime.now() + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")


def public_user(conn: sqlite3.Connection, user: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    user_dict = dict(user)
    assignee = None
    if user_dict["assignee_id"]:
        assignee = row_to_dict(conn.execute("SELECT * FROM assignees WHERE id = ?", (user_dict["assignee_id"],)).fetchone())
    return {
        "id": user_dict["id"],
        "username": user_dict["username"],
        "display_name": user_dict["display_name"],
        "assignee_id": user_dict["assignee_id"],
        "assignee": assignee,
        "role": user_dict["role"],
        "password_must_change": bool(user_dict.get("password_must_change", 0)),
    }


def current_user(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="ログインしてください")
    token = authorization.removeprefix("Bearer ").strip()
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso(),))
        row = conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ? AND users.active = 1
            """,
            (token, now_iso()),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="ログインしてください")
        return public_user(conn, row)


def require_ready_user(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user.get("password_must_change"):
        raise HTTPException(status_code=403, detail="初回パスワード変更が必要です")
    return user


def require_admin(user: dict[str, Any]) -> None:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")

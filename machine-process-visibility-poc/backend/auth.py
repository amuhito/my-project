from __future__ import annotations

import hashlib
from typing import Any, Optional

import sqlite3
from fastapi import Header, HTTPException

from database import db, row_to_dict


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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
    }


def current_user(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="ログインしてください")
    token = authorization.removeprefix("Bearer ").strip()
    with db() as conn:
        row = conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND users.active = 1
            """,
            (token,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="ログインしてください")
        return public_user(conn, row)

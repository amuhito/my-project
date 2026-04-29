from __future__ import annotations

import secrets
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from auth import current_user, hash_password, public_user
from database import db
from schemas import LoginPayload
from utils import now_iso


router = APIRouter(prefix="/api/auth")


@router.post("/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    with db() as conn:
        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND password_hash = ? AND active = 1
            """,
            (payload.username.strip(), hash_password(payload.password)),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="ユーザー名またはパスワードが違います")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions(token, user_id, created_at) VALUES (?, ?, ?)", (token, user["id"], now_iso()))
        return {"token": token, "user": public_user(conn, user)}


@router.get("/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return user


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None), user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    return {"status": "ok"}

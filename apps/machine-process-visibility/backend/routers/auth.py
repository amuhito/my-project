from __future__ import annotations

import secrets
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from auth import current_user, hash_password, public_user, session_expiry_iso, verify_password
from database import db
from schemas import ChangePasswordPayload, LoginPayload
from utils import now_iso


router = APIRouter(prefix="/api/auth")


@router.post("/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    with db() as conn:
        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND active = 1
            """,
            (payload.username.strip(),),
        ).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="ユーザー名またはパスワードが違います")
        if not user["password_hash"].startswith("$2"):
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(payload.password), user["id"]))
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user["id"], now_iso(), session_expiry_iso()),
        )
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


@router.post("/change-password")
def change_password(payload: ChangePasswordPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="新しいパスワードは8文字以上で入力してください")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="現在と異なるパスワードを設定してください")
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ? AND active = 1", (user["id"],)).fetchone()
        if not row or not verify_password(payload.current_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="現在のパスワードが違います")
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?, password_must_change = 0, password_changed_at = ?
            WHERE id = ?
            """,
            (hash_password(payload.new_password), now_iso(), user["id"]),
        )
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        return public_user(conn, updated)

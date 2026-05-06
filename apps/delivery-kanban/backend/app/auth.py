from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .database import get_connection

PASSWORD_ITERATIONS = 200_000
DEFAULT_SESSION_HOURS = 12


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str
    display_name: str


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _datetime_text(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _parse_datetime_text(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def _hash_password(password: str, salt_hex: str) -> str:
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PASSWORD_ITERATIONS,
    )
    return hashed.hex()


def ensure_default_user() -> None:
    username = os.getenv("KANBAN_INITIAL_USERNAME", "admin").strip() or "admin"
    display_name = os.getenv("KANBAN_INITIAL_DISPLAY_NAME", "管理者").strip() or "管理者"
    password = os.getenv("KANBAN_INITIAL_PASSWORD", "admin1234")

    with get_connection() as connection:
        exists = connection.execute("SELECT id FROM user_account LIMIT 1").fetchone()
        if exists is not None:
            return

        salt_hex = secrets.token_hex(16)
        password_hash = _hash_password(password, salt_hex)
        connection.execute(
            """
            INSERT INTO user_account (username, display_name, password_hash, password_salt, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, display_name, password_hash, salt_hex, _datetime_text(_utc_now())),
        )


def create_user(username: str, display_name: str, password: str) -> AuthUser:
    normalized_username = username.strip()
    normalized_display_name = display_name.strip()

    if not normalized_username:
        raise ValueError("ユーザー名は必須です。")
    if not normalized_display_name:
        raise ValueError("表示名は必須です。")
    if len(password) < 8:
        raise ValueError("パスワードは8文字以上で設定してください。")

    with get_connection() as connection:
        exists = connection.execute(
            "SELECT id FROM user_account WHERE username = ? LIMIT 1",
            (normalized_username,),
        ).fetchone()
        if exists is not None:
            raise ValueError("同じユーザー名が既に存在します。")

        salt_hex = secrets.token_hex(16)
        password_hash = _hash_password(password, salt_hex)
        cursor = connection.execute(
            """
            INSERT INTO user_account (username, display_name, password_hash, password_salt, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                normalized_username,
                normalized_display_name,
                password_hash,
                salt_hex,
                _datetime_text(_utc_now()),
            ),
        )
        user_id = cursor.lastrowid

    return AuthUser(id=user_id, username=normalized_username, display_name=normalized_display_name)


def list_users() -> list[AuthUser]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, username, display_name
            FROM user_account
            ORDER BY id ASC
            """
        ).fetchall()
    return [
        AuthUser(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
        )
        for row in rows
    ]


def authenticate_user(username: str, password: str) -> AuthUser | None:
    normalized_username = username.strip()
    if not normalized_username or not password:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, display_name, password_hash, password_salt
            FROM user_account
            WHERE username = ?
            LIMIT 1
            """,
            (normalized_username,),
        ).fetchone()
        if row is None:
            return None

        if not secrets.compare_digest(row["password_hash"], _hash_password(password, row["password_salt"])):
            return None

        return AuthUser(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
        )


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(40)
    session_hours = int(os.getenv("KANBAN_SESSION_HOURS", str(DEFAULT_SESSION_HOURS)))
    expires_at = _utc_now() + timedelta(hours=max(session_hours, 1))

    with get_connection() as connection:
        connection.execute("DELETE FROM user_session WHERE expires_at <= ?", (_datetime_text(_utc_now()),))
        connection.execute(
            """
            INSERT INTO user_session (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, _datetime_text(_utc_now()), _datetime_text(expires_at)),
        )
    return token


def revoke_session(token: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM user_session WHERE token = ?", (token,))


def resolve_user_by_token(token: str) -> AuthUser | None:
    if not token:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                user_account.id,
                user_account.username,
                user_account.display_name,
                user_session.expires_at
            FROM user_session
            JOIN user_account ON user_account.id = user_session.user_id
            WHERE user_session.token = ?
            LIMIT 1
            """,
            (token,),
        ).fetchone()
        if row is None:
            return None

        expires_at = _parse_datetime_text(row["expires_at"])
        if expires_at <= _utc_now():
            connection.execute("DELETE FROM user_session WHERE token = ?", (token,))
            return None

        return AuthUser(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
        )

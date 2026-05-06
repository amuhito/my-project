from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

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
from auth import verify_password
from conftest import fetch_all, fetch_one, user_by_username
from database import db
from schemas import ActivePayload, AssigneePayload, TagPayload


def test_list_admin_users_includes_assignee_name(initialized_db: Path) -> None:
    users = list_admin_users()

    assert users[0]["username"] == "admin"
    assert next(user for user in users if user["username"] == "mitani")["assignee_name"] == "三谷"


def test_admin_cannot_deactivate_self(initialized_db: Path) -> None:
    admin = user_by_username("admin")

    with pytest.raises(HTTPException) as exc_info:
        update_user_active_status(admin["id"], ActivePayload(active=False), admin)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "自分自身は無効化できません"


def test_deactivating_user_deletes_sessions(initialized_db: Path) -> None:
    admin = user_by_username("admin")
    user = user_by_username("mitani")
    with db() as conn:
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            ("token-1", user["id"], "2026-05-05T10:00:00", "2026-05-05T22:00:00"),
        )

    updated = update_user_active_status(user["id"], ActivePayload(active=False), admin)

    assert updated["active"] == 0
    assert fetch_all("SELECT * FROM sessions WHERE user_id = ?", (user["id"],)) == []


def test_reset_password_sets_must_change_and_deletes_sessions(initialized_db: Path) -> None:
    user = user_by_username("yamamoto")
    with db() as conn:
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            ("token-2", user["id"], "2026-05-05T10:00:00", "2026-05-05T22:00:00"),
        )

    result = reset_password_for_user(user["id"])
    updated = user_by_username("yamamoto")

    assert len(result["temporary_password"]) > 8
    assert updated["password_must_change"] == 1
    assert updated["password_changed_at"] is None
    assert verify_password(result["temporary_password"], updated["password_hash"])
    assert fetch_all("SELECT * FROM sessions WHERE user_id = ?", (user["id"],)) == []


def test_update_assignee_detail_and_active_status(initialized_db: Path) -> None:
    assignee = fetch_one("SELECT * FROM assignees WHERE name = ?", ("佐藤",))

    updated = update_assignee_detail(
        assignee["id"],
        AssigneePayload(name="  佐藤A  ", color="  #111111  ", active=False),
    )
    active_updated = update_assignee_active_status(assignee["id"], ActivePayload(active=True))

    assert updated["name"] == "佐藤A"
    assert updated["color"] == "#111111"
    assert updated["active"] == 0
    assert active_updated["active"] == 1
    assert len(list_admin_assignees()) == 5


def test_create_update_and_delete_tag(initialized_db: Path) -> None:
    created = create_tag_for_admin(TagPayload(name="  治具待ち  ", color="  #222222  "))
    updated = update_tag_detail(created["id"], TagPayload(name="治具確認", color="#333333"))

    assert created["name"] == "治具待ち"
    assert created["color"] == "#222222"
    assert updated["name"] == "治具確認"
    assert updated["color"] == "#333333"

    assert delete_tag_for_admin(created["id"]) == {"status": "ok"}
    assert all(tag["id"] != created["id"] for tag in list_admin_tags())


def test_delete_tag_removes_card_tag_links(initialized_db: Path) -> None:
    tag = fetch_one("SELECT * FROM tags WHERE name = ?", ("追加工",))
    assert fetch_all("SELECT * FROM card_tags WHERE tag_id = ?", (tag["id"],))

    delete_tag_for_admin(tag["id"])

    assert fetch_all("SELECT * FROM card_tags WHERE tag_id = ?", (tag["id"],)) == []

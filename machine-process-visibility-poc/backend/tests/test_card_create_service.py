from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from card_create_service import create_card_for_user
from schemas import CardPayload
from conftest import fetch_all, fetch_one, user_by_username


def new_card_payload(**overrides: Any) -> CardPayload:
    process = fetch_one("SELECT * FROM processes WHERE name = ?", ("機械加工",))
    assignee = fetch_one("SELECT * FROM assignees WHERE name = ?", ("佐藤",))
    tag = fetch_one("SELECT * FROM tags WHERE name = ?", ("追加工",))
    values = {
        "order_no": "N-12345",
        "item_type": "09",
        "drawing_no": "NEW-001",
        "item_name": "新規加工品",
        "remarks": "  初回投入  ",
        "total_qty": 5,
        "completed_qty": 3,
        "current_process_id": process["id"],
        "status": "完了",
        "assignee_id": assignee["id"],
        "planned_work_date": "2026-05-05",
        "due_date": "2026-05-12",
        "description": "新規カード",
        "tag_ids": [tag["id"]],
    }
    values.update(overrides)
    return CardPayload(**values)


def test_admin_can_create_card_with_initial_status_tags_and_audit(initialized_db: Path) -> None:
    admin = user_by_username("admin")

    created = create_card_for_user(new_card_payload(), admin)

    assert created["order_no"] == "N-12345"
    assert created["remarks"] == "初回投入"
    assert created["completed_qty"] == 0
    assert created["status"] == "未着手"
    assert [tag["name"] for tag in created["tags"]] == ["追加工"]

    audit = fetch_one("SELECT * FROM card_audit_logs WHERE card_id = ?", (created["id"],))
    assert audit["action"] == "card_created"
    assert audit["before_json"] is None
    assert json.loads(audit["after_json"])["drawing_no"] == "NEW-001"


def test_operator_cannot_create_card(initialized_db: Path) -> None:
    operator = user_by_username("sato")

    with pytest.raises(HTTPException) as exc_info:
        create_card_for_user(new_card_payload(), operator)

    assert exc_info.value.status_code == 403
    assert fetch_all("SELECT * FROM cards WHERE drawing_no = ?", ("NEW-001",)) == []

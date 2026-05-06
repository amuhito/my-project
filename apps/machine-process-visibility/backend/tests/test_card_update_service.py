from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from card_update_service import update_card_for_user
from conftest import card_by_drawing_no, card_payload, fetch_all, fetch_one, user_by_username


def test_operator_can_update_non_admin_card_fields(initialized_db: Path) -> None:
    card = card_by_drawing_no("SH-208500L2")
    user = user_by_username("mitani")

    updated = update_card_for_user(
        card["id"],
        card_payload(card, item_name="シュート 改訂", remarks="現場確認済み"),
        user,
    )

    assert updated["item_name"] == "シュート 改訂"
    assert updated["remarks"] == "現場確認済み"
    audit = fetch_one("SELECT * FROM card_audit_logs WHERE card_id = ?", (card["id"],))
    assert audit["action"] == "card_updated"
    assert json.loads(audit["after_json"])["item_name"] == "シュート 改訂"


def test_operator_cannot_update_admin_only_card_fields(initialized_db: Path) -> None:
    card = card_by_drawing_no("SH-208500L2")
    user = user_by_username("mitani")

    with pytest.raises(HTTPException) as exc_info:
        update_card_for_user(card["id"], card_payload(card, total_qty=99), user)

    assert exc_info.value.status_code == 403


def test_completed_quantity_must_be_updated_through_work_results(initialized_db: Path) -> None:
    card = card_by_drawing_no("HB-110470")
    admin = user_by_username("admin")

    with pytest.raises(HTTPException) as exc_info:
        update_card_for_user(card["id"], card_payload(card, completed_qty=1), admin)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "完了数は作業実績の数量増減で更新してください"


def test_status_must_be_updated_through_work_results(initialized_db: Path) -> None:
    card = card_by_drawing_no("HB-110470")
    admin = user_by_username("admin")

    with pytest.raises(HTTPException) as exc_info:
        update_card_for_user(card["id"], card_payload(card, status="完了"), admin)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "ステータスは作業実績の登録に連動して更新します"


def test_admin_update_writes_specific_process_and_assignee_audit_logs(initialized_db: Path) -> None:
    card = card_by_drawing_no("HB-110470")
    admin = user_by_username("admin")
    process = fetch_one("SELECT * FROM processes WHERE name = ?", ("機械加工",))
    assignee = fetch_one("SELECT * FROM assignees WHERE name = ?", ("佐藤",))

    updated = update_card_for_user(
        card["id"],
        card_payload(card, current_process_id=process["id"], assignee_id=assignee["id"]),
        admin,
    )

    assert updated["current_process_id"] == process["id"]
    assert updated["assignee_id"] == assignee["id"]
    actions = [
        row["action"]
        for row in fetch_all("SELECT action FROM card_audit_logs WHERE card_id = ? ORDER BY id", (card["id"],))
    ]
    assert actions == ["card_updated", "process_changed", "assignee_changed"]

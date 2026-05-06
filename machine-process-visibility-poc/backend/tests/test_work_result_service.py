from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from schemas import WorkResultPayload
from work_result_service import register_work_result_for_card, status_for_completed_qty
from conftest import card_by_drawing_no, fetch_one, user_by_username


def test_status_for_completed_qty() -> None:
    assert status_for_completed_qty(0, 8) == "未着手"
    assert status_for_completed_qty(3, 8) == "作業中"
    assert status_for_completed_qty(8, 8) == "完了"


def test_register_work_result_completes_card_and_writes_log_and_audit(initialized_db: Path) -> None:
    card = card_by_drawing_no("HB-110470")
    user = user_by_username("yamamoto")
    payload = WorkResultPayload(
        completed_qty_delta=8,
        work_hours=2.5,
        assignee_id=user["assignee_id"],
        work_date="2026-05-05",
        comment_type="作業",
        comment="",
    )

    result = register_work_result_for_card(card["id"], payload, user)

    assert result["completed_qty"] == 8
    assert result["status"] == "完了"
    assert result["work_logs"][0]["completed_qty_delta"] == 8
    assert result["work_logs"][0]["work_hours"] == 2.5

    audit = fetch_one("SELECT * FROM card_audit_logs WHERE card_id = ?", (card["id"],))
    assert audit["action"] == "completed_qty_from_work_log"
    assert json.loads(audit["before_json"]) == {"completed_qty": 0}
    assert json.loads(audit["after_json"])["work_log_delta"] == 8


def test_rework_requires_negative_delta_and_comment(initialized_db: Path) -> None:
    card = card_by_drawing_no("SH-208500L2")
    user = user_by_username("mitani")

    with pytest.raises(HTTPException) as exc_info:
        register_work_result_for_card(
            card["id"],
            WorkResultPayload(
                completed_qty_delta=-1,
                work_hours=0,
                assignee_id=user["assignee_id"],
                work_date="2026-05-05",
                comment_type="手戻り",
                comment="",
            ),
            user,
        )
    assert exc_info.value.status_code == 400

    result = register_work_result_for_card(
        card["id"],
        WorkResultPayload(
            completed_qty_delta=-1,
            work_hours=0,
            assignee_id=user["assignee_id"],
            work_date="2026-05-05",
            comment_type="手戻り",
            comment="寸法確認のため差し戻し",
        ),
        user,
    )

    assert result["completed_qty"] == 14
    assert result["status"] == "作業中"
    assert result["comments"][0]["comment_type"] == "手戻り"
    assert result["comments"][0]["body"] == "寸法確認のため差し戻し"


def test_operator_cannot_register_work_for_other_assignee(initialized_db: Path) -> None:
    card = card_by_drawing_no("SH-208500L2")
    user = user_by_username("mitani")
    other_assignee = fetch_one("SELECT * FROM assignees WHERE name = ?", ("山本",))

    with pytest.raises(HTTPException) as exc_info:
        register_work_result_for_card(
            card["id"],
            WorkResultPayload(
                completed_qty_delta=1,
                work_hours=1,
                assignee_id=other_assignee["id"],
                work_date="2026-05-05",
                comment_type="作業",
                comment="",
            ),
            user,
        )

    assert exc_info.value.status_code == 403


def test_completed_quantity_cannot_exceed_total(initialized_db: Path) -> None:
    card = card_by_drawing_no("HB-110470")
    user = user_by_username("yamamoto")

    with pytest.raises(HTTPException) as exc_info:
        register_work_result_for_card(
            card["id"],
            WorkResultPayload(
                completed_qty_delta=9,
                work_hours=1,
                assignee_id=user["assignee_id"],
                work_date="2026-05-05",
                comment_type="作業",
                comment="",
            ),
            user,
        )

    assert exc_info.value.status_code == 400

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from card_query_service import get_card_detail, list_cards_for_user
from conftest import card_by_drawing_no, fetch_one


def test_list_cards_returns_due_date_order(initialized_db: Path) -> None:
    cards = list_cards_for_user()

    assert [card["drawing_no"] for card in cards] == ["RW-001", "SH-208500L2", "HB-110470"]
    assert cards[0]["assignee"]["name"] == "佐藤"
    assert cards[0]["process"]["name"] == "機械加工"


def test_list_cards_filters_by_process_assignee_and_tag(initialized_db: Path) -> None:
    card = card_by_drawing_no("RW-001")

    by_process = list_cards_for_user(process_id=card["current_process_id"])
    by_assignee = list_cards_for_user(assignee_id=card["assignee_id"])
    by_tag = list_cards_for_user(tag="追加工")

    assert [item["drawing_no"] for item in by_process] == ["RW-001"]
    assert [item["drawing_no"] for item in by_assignee] == ["RW-001"]
    assert [item["drawing_no"] for item in by_tag] == ["RW-001"]


def test_get_card_detail_includes_comments_and_work_logs(initialized_db: Path) -> None:
    card = card_by_drawing_no("SH-208500L2")
    assignee = fetch_one("SELECT * FROM assignees WHERE name = ?", ("三谷",))
    with_card_id = (card["id"],)
    from database import db

    with db() as conn:
        comment = conn.execute(
            "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (*with_card_id, "コメント", "確認済み", assignee["id"], "2026-05-05T10:00:00"),
        )
        conn.execute(
            """
            INSERT INTO work_logs(
                card_id, assignee_id, registered_by_user_id, process_id, work_type, work_date,
                completed_qty_delta, work_hours, comment_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card["id"],
                assignee["id"],
                None,
                card["current_process_id"],
                "コメント",
                "2026-05-05",
                0,
                0,
                comment.lastrowid,
                "2026-05-05T10:00:00",
            ),
        )

    detail = get_card_detail(card["id"])

    assert detail["comments"][0]["body"] == "確認済み"
    assert detail["work_logs"][0]["comment_body"] == "確認済み"


def test_get_card_detail_raises_404_for_unknown_card(initialized_db: Path) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_card_detail(9999)

    assert exc_info.value.status_code == 404

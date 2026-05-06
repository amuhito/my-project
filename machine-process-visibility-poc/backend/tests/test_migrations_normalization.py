from __future__ import annotations

from pathlib import Path

from conftest import fetch_all, fetch_one
from database import db
from migrations import init_db, normalize_compact_date


def test_normalize_compact_date() -> None:
    assert normalize_compact_date("20260425") == "2026-04-25"
    assert normalize_compact_date("2026-04-25") == "2026-04-25"
    assert normalize_compact_date("") == ""
    assert normalize_compact_date(None) is None


def test_init_db_normalizes_existing_invalid_poc_card_data(initialized_db: Path) -> None:
    card = fetch_one("SELECT * FROM cards WHERE drawing_no = ?", ("HB-110470",))
    with db() as conn:
        conn.execute(
            """
            UPDATE cards
            SET order_no = ?, item_type = ?, due_date = ?
            WHERE id = ?
            """,
            ("ORD-2026-002", "刃物", "20260425", card["id"]),
        )

    init_db()
    updated = fetch_one("SELECT * FROM cards WHERE id = ?", (card["id"],))

    assert updated["order_no"] == "S-26654"
    assert updated["item_type"] == "02"
    assert updated["due_date"] == "2026-04-25"


def test_init_db_removes_invalid_work_logs(initialized_db: Path) -> None:
    card = fetch_one("SELECT * FROM cards WHERE drawing_no = ?", ("SH-208500L2",))
    assignee = fetch_one("SELECT * FROM assignees WHERE name = ?", ("三谷",))
    with db() as conn:
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
                "作業",
                "2026-05-05",
                0,
                12,
                None,
                "2026-05-05T10:00:00",
            ),
        )

    init_db()

    assert fetch_all("SELECT * FROM work_logs WHERE card_id = ?", (card["id"],)) == []

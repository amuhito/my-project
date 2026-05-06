from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database
from migrations import init_db
from schemas import CardPayload


@pytest.fixture()
def initialized_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "machine_poc_test.sqlite3"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    init_db()
    return db_path


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    with database.db() as conn:
        return dict(conn.execute(sql, params).fetchone())


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with database.db() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def user_by_username(username: str) -> dict[str, Any]:
    return fetch_one("SELECT * FROM users WHERE username = ?", (username,))


def card_by_drawing_no(drawing_no: str) -> dict[str, Any]:
    return fetch_one("SELECT * FROM cards WHERE drawing_no = ?", (drawing_no,))


def card_payload(card: dict[str, Any], **overrides: Any) -> CardPayload:
    tag_ids = [row["tag_id"] for row in fetch_all("SELECT tag_id FROM card_tags WHERE card_id = ? ORDER BY tag_id", (card["id"],))]
    values = {
        "order_no": card["order_no"],
        "item_type": card["item_type"],
        "drawing_no": card["drawing_no"],
        "item_name": card["item_name"],
        "remarks": card["remarks"],
        "total_qty": card["total_qty"],
        "completed_qty": card["completed_qty"],
        "current_process_id": card["current_process_id"],
        "status": card["status"],
        "assignee_id": card["assignee_id"],
        "planned_work_date": card["planned_work_date"],
        "due_date": card["due_date"],
        "description": card["description"],
        "tag_ids": tag_ids,
    }
    values.update(overrides)
    return CardPayload(**values)

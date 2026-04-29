from __future__ import annotations

import re
import sqlite3
from typing import Any

from fastapi import HTTPException

from database import row_to_dict
from schemas import CardPayload
from utils import validate_iso_date


ORDER_NO_PATTERN = re.compile(r"^[A-Z]-\d{5}$")
ITEM_TYPE_PATTERN = re.compile(r"^\d{2}$")


def validate_card_payload(payload: CardPayload) -> None:
    order_no = payload.order_no.strip()
    item_type = payload.item_type.strip()
    if order_no and not ORDER_NO_PATTERN.fullmatch(order_no):
        raise HTTPException(status_code=400, detail="受注番号は E-25086 のように 英字1文字-5桁 で入力してください")
    if item_type and not ITEM_TYPE_PATTERN.fullmatch(item_type):
        raise HTTPException(status_code=400, detail="種別は2桁の数字で入力してください")
    if payload.completed_qty > payload.total_qty:
        raise HTTPException(status_code=400, detail="完了数は総数を超えられません")
    if payload.status not in {"未着手", "作業中", "完了"}:
        raise HTTPException(status_code=400, detail="不正なステータスです")
    validate_iso_date(payload.planned_work_date, "予定作業日")
    validate_iso_date(payload.due_date, "納期")


def hydrate_card(conn: sqlite3.Connection, card_row: sqlite3.Row) -> dict[str, Any]:
    card = dict(card_row)
    card["progress_rate"] = round((card["completed_qty"] / card["total_qty"]) * 100) if card["total_qty"] else 0
    card["assignee"] = row_to_dict(
        conn.execute("SELECT * FROM assignees WHERE id = ?", (card["assignee_id"],)).fetchone()
    )
    card["process"] = row_to_dict(
        conn.execute("SELECT * FROM processes WHERE id = ?", (card["current_process_id"],)).fetchone()
    )
    card["tags"] = [
        dict(row)
        for row in conn.execute(
            """
            SELECT t.* FROM tags t
            JOIN card_tags ct ON ct.tag_id = t.id
            WHERE ct.card_id = ?
            ORDER BY t.id
            """,
            (card["id"],),
        ).fetchall()
    ]
    return card


def get_card_or_404(conn: sqlite3.Connection, card_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="カードが見つかりません")
    return hydrate_card(conn, row)


def get_card_detail_or_404(conn: sqlite3.Connection, card_id: int) -> dict[str, Any]:
    card = get_card_or_404(conn, card_id)
    card["comments"] = [
        dict(row)
        for row in conn.execute(
            """
            SELECT comments.*, assignees.name AS user_name
            FROM comments
            LEFT JOIN assignees ON assignees.id = comments.user_id
            WHERE comments.card_id = ?
            ORDER BY comments.created_at DESC, comments.id DESC
            """,
            (card_id,),
        ).fetchall()
    ]
    card["work_logs"] = [
        dict(row)
        for row in conn.execute(
            """
            SELECT wl.*, a.name AS assignee_name, COALESCE(wl.work_type, c.comment_type) AS comment_type, c.body AS comment_body
            FROM work_logs wl
            LEFT JOIN assignees a ON a.id = wl.assignee_id
            LEFT JOIN comments c ON c.id = wl.comment_id
            WHERE wl.card_id = ?
            ORDER BY wl.created_at DESC, wl.id DESC
            """,
            (card_id,),
        ).fetchall()
    ]
    return card

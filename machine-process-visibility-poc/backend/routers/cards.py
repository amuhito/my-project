from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from auth import current_user
from card_service import get_card_detail_or_404, get_card_or_404, hydrate_card, validate_card_payload
from constants import COMMENT_TYPES
from database import db
from schemas import CardPayload, CommentPayload, WorkResultPayload
from utils import now_iso, validate_iso_date


router = APIRouter(prefix="/api/cards")


@router.get("")
def list_cards(
    process_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    tag: Optional[str] = None,
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if process_id:
        where.append("c.current_process_id = ?")
        params.append(process_id)
    if assignee_id:
        where.append("c.assignee_id = ?")
        params.append(assignee_id)
    if tag:
        where.append("EXISTS (SELECT 1 FROM card_tags ct JOIN tags t ON t.id = ct.tag_id WHERE ct.card_id = c.id AND t.name = ?)")
        params.append(tag)
    sql = "SELECT c.* FROM cards c"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY c.due_date IS NULL, c.due_date, c.id"
    with db() as conn:
        return [hydrate_card(conn, row) for row in conn.execute(sql, params).fetchall()]


@router.post("")
def create_card(payload: CardPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    validate_card_payload(payload)
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO cards(
                order_no, item_type, drawing_no, item_name, remarks,
                total_qty, completed_qty, current_process_id, status,
                assignee_id, planned_work_date, due_date, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.order_no.strip(),
                payload.item_type.strip(),
                payload.drawing_no,
                payload.item_name,
                payload.remarks.strip(),
                payload.total_qty,
                payload.completed_qty,
                payload.current_process_id,
                payload.status,
                payload.assignee_id,
                payload.planned_work_date,
                payload.due_date,
                payload.description,
                now_iso(),
                now_iso(),
            ),
        )
        card_id = cur.lastrowid
        for tag_id in payload.tag_ids:
            conn.execute("INSERT OR IGNORE INTO card_tags(card_id, tag_id) VALUES (?, ?)", (card_id, tag_id))
        return get_card_or_404(conn, card_id)


@router.get("/{card_id}")
def card_detail(card_id: int, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with db() as conn:
        return get_card_detail_or_404(conn, card_id)


@router.put("/{card_id}")
def update_card(card_id: int, payload: CardPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    validate_card_payload(payload)
    with db() as conn:
        get_card_or_404(conn, card_id)
        conn.execute(
            """
            UPDATE cards SET
                order_no = ?, item_type = ?, drawing_no = ?, item_name = ?, remarks = ?,
                total_qty = ?, completed_qty = ?,
                current_process_id = ?, status = ?, assignee_id = ?, planned_work_date = ?,
                due_date = ?, description = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.order_no.strip(),
                payload.item_type.strip(),
                payload.drawing_no,
                payload.item_name,
                payload.remarks.strip(),
                payload.total_qty,
                payload.completed_qty,
                payload.current_process_id,
                payload.status,
                payload.assignee_id,
                payload.planned_work_date,
                payload.due_date,
                payload.description,
                now_iso(),
                card_id,
            ),
        )
        conn.execute("DELETE FROM card_tags WHERE card_id = ?", (card_id,))
        for tag_id in payload.tag_ids:
            conn.execute("INSERT OR IGNORE INTO card_tags(card_id, tag_id) VALUES (?, ?)", (card_id, tag_id))
        return get_card_or_404(conn, card_id)


@router.post("/{card_id}/comments")
def add_comment(card_id: int, payload: CommentPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正なコメント種別です")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="コメントを入力してください")
    with db() as conn:
        get_card_or_404(conn, card_id)
        user_id = user["assignee_id"] or payload.user_id
        cur = conn.execute(
            "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (card_id, payload.comment_type, payload.body.strip(), user_id, now_iso()),
        )
        return dict(conn.execute("SELECT * FROM comments WHERE id = ?", (cur.lastrowid,)).fetchone())


@router.post("/{card_id}/work-results")
def register_work_result(card_id: int, payload: WorkResultPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正なコメント種別です")
    work_date = validate_iso_date(payload.work_date, "作業日") or date.today().isoformat()
    if payload.completed_qty_delta == 0 and payload.work_hours == 0 and not payload.comment.strip():
        raise HTTPException(status_code=400, detail="作業実績を入力してください")
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        card = get_card_or_404(conn, card_id)
        new_completed = card["completed_qty"] + payload.completed_qty_delta
        if new_completed > card["total_qty"]:
            raise HTTPException(status_code=400, detail="今回完了数を加えると総数を超えます")
        comment_id = None
        worker_id = payload.assignee_id or user["assignee_id"] or card["assignee_id"]
        if payload.comment.strip():
            cur = conn.execute(
                "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (card_id, payload.comment_type, payload.comment.strip(), worker_id, now_iso()),
            )
            comment_id = cur.lastrowid
        status = "完了" if new_completed >= card["total_qty"] else ("作業中" if new_completed > 0 else card["status"])
        conn.execute(
            "UPDATE cards SET completed_qty = ?, status = ?, updated_at = ? WHERE id = ?",
            (new_completed, status, now_iso(), card_id),
        )
        conn.execute(
            """
            INSERT INTO work_logs(card_id, assignee_id, process_id, work_date, completed_qty_delta, work_hours, comment_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                worker_id,
                card["current_process_id"],
                work_date,
                payload.completed_qty_delta,
                payload.work_hours,
                comment_id,
                now_iso(),
            ),
        )
        return get_card_detail_or_404(conn, card_id)

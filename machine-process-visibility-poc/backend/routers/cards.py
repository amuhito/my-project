from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from audit import write_card_audit
from auth import require_admin, require_ready_user
from card_service import get_card_detail_or_404, get_card_or_404, hydrate_card, validate_card_payload
from constants import COMMENT_TYPES
from database import db
from schemas import CardPayload, CommentPayload, WorkResultPayload
from utils import now_iso, validate_iso_date


router = APIRouter(prefix="/api/cards")


ADMIN_ONLY_CARD_FIELDS = {
    "order_no",
    "item_type",
    "drawing_no",
    "total_qty",
    "completed_qty",
    "current_process_id",
    "status",
    "assignee_id",
}


def card_change_snapshot(card: dict[str, Any]) -> dict[str, Any]:
    return {
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
        "tag_ids": [tag["id"] for tag in card.get("tags", [])],
    }


def payload_snapshot(payload: CardPayload) -> dict[str, Any]:
    return {
        "order_no": payload.order_no.strip(),
        "item_type": payload.item_type.strip(),
        "drawing_no": payload.drawing_no,
        "item_name": payload.item_name,
        "remarks": payload.remarks.strip(),
        "total_qty": payload.total_qty,
        "completed_qty": payload.completed_qty,
        "current_process_id": payload.current_process_id,
        "status": payload.status,
        "assignee_id": payload.assignee_id,
        "planned_work_date": payload.planned_work_date,
        "due_date": payload.due_date,
        "description": payload.description,
        "tag_ids": payload.tag_ids,
    }


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [key for key, value in after.items() if before.get(key) != value]


@router.get("")
def list_cards(
    process_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    tag: Optional[str] = None,
    user: dict[str, Any] = Depends(require_ready_user),
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
def create_card(payload: CardPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    require_admin(user)
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
        created = get_card_or_404(conn, card_id)
        write_card_audit(conn, card_id, user["id"], "card_created", None, card_change_snapshot(created))
        return created


@router.get("/{card_id}")
def card_detail(card_id: int, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    with db() as conn:
        return get_card_detail_or_404(conn, card_id)


@router.put("/{card_id}")
def update_card(card_id: int, payload: CardPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    validate_card_payload(payload)
    with db() as conn:
        before_card = get_card_or_404(conn, card_id)
        before = card_change_snapshot(before_card)
        after = payload_snapshot(payload)
        changed = changed_fields(before, after)
        if user["role"] != "admin" and any(field in ADMIN_ONLY_CARD_FIELDS for field in changed):
            raise HTTPException(status_code=403, detail="この項目の変更には管理者権限が必要です")
        if "completed_qty" in changed and not payload.completed_qty_reason.strip():
            raise HTTPException(status_code=400, detail="完了数を直接修正する場合は理由コメントを入力してください")
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
        updated = get_card_or_404(conn, card_id)
        updated_snapshot = card_change_snapshot(updated)
        if changed:
            write_card_audit(conn, card_id, user["id"], "card_updated", before, updated_snapshot)
        if "current_process_id" in changed:
            write_card_audit(conn, card_id, user["id"], "process_changed", {"current_process_id": before["current_process_id"]}, {"current_process_id": updated_snapshot["current_process_id"]})
        if "completed_qty" in changed:
            reason = payload.completed_qty_reason.strip()
            conn.execute(
                "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (card_id, "補足", f"完了数手修正: {reason}", user["assignee_id"], now_iso()),
            )
            write_card_audit(
                conn,
                card_id,
                user["id"],
                "completed_qty_adjusted",
                {"completed_qty": before["completed_qty"]},
                {"completed_qty": updated_snapshot["completed_qty"], "reason": reason},
            )
        if "assignee_id" in changed:
            write_card_audit(conn, card_id, user["id"], "assignee_changed", {"assignee_id": before["assignee_id"]}, {"assignee_id": updated_snapshot["assignee_id"]})
        return updated


@router.post("/{card_id}/comments")
def add_comment(card_id: int, payload: CommentPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正なコメント種別です")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="コメントを入力してください")
    if payload.user_id and payload.user_id != user["assignee_id"]:
        require_admin(user)
    with db() as conn:
        get_card_or_404(conn, card_id)
        user_id = user["assignee_id"] or payload.user_id
        cur = conn.execute(
            "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (card_id, payload.comment_type, payload.body.strip(), user_id, now_iso()),
        )
        return dict(conn.execute("SELECT * FROM comments WHERE id = ?", (cur.lastrowid,)).fetchone())


@router.post("/{card_id}/work-results")
def register_work_result(card_id: int, payload: WorkResultPayload, user: dict[str, Any] = Depends(require_ready_user)) -> dict[str, Any]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正なコメント種別です")
    work_date = validate_iso_date(payload.work_date, "作業日") or date.today().isoformat()
    if payload.completed_qty_delta == 0 and payload.work_hours == 0 and not payload.comment.strip():
        raise HTTPException(status_code=400, detail="作業実績を入力してください")
    if payload.assignee_id and payload.assignee_id != user["assignee_id"]:
        require_admin(user)
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
            INSERT INTO work_logs(
                card_id, assignee_id, registered_by_user_id, process_id, work_date,
                completed_qty_delta, work_hours, comment_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                worker_id,
                user["id"],
                card["current_process_id"],
                work_date,
                payload.completed_qty_delta,
                payload.work_hours,
                comment_id,
                now_iso(),
            ),
        )
        if payload.completed_qty_delta:
            write_card_audit(
                conn,
                card_id,
                user["id"],
                "completed_qty_from_work_log",
                {"completed_qty": card["completed_qty"]},
                {"completed_qty": new_completed, "work_log_delta": payload.completed_qty_delta, "assignee_id": worker_id},
            )
        return get_card_detail_or_404(conn, card_id)

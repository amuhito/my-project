from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from audit import write_card_audit
from card_service import get_card_or_404, validate_card_payload
from database import db
from schemas import CardPayload
from utils import now_iso


ADMIN_ONLY_CARD_FIELDS = {
    "order_no",
    "item_type",
    "drawing_no",
    "total_qty",
    "current_process_id",
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


def ensure_card_update_allowed(changed: list[str], user: dict[str, Any]) -> None:
    if user["role"] != "admin" and any(field in ADMIN_ONLY_CARD_FIELDS for field in changed):
        raise HTTPException(status_code=403, detail="この項目の変更には管理者権限が必要です")
    if "completed_qty" in changed:
        raise HTTPException(status_code=400, detail="完了数は作業実績の数量増減で更新してください")
    if "status" in changed:
        raise HTTPException(status_code=400, detail="ステータスは作業実績の登録に連動して更新します")


def update_card_for_user(card_id: int, payload: CardPayload, user: dict[str, Any]) -> dict[str, Any]:
    validate_card_payload(payload)
    with db() as conn:
        before_card = get_card_or_404(conn, card_id)
        before = card_change_snapshot(before_card)
        after = payload_snapshot(payload)
        changed = changed_fields(before, after)
        ensure_card_update_allowed(changed, user)

        conn.execute(
            """
            UPDATE cards SET
                order_no = ?, item_type = ?, drawing_no = ?, item_name = ?, remarks = ?,
                total_qty = ?,
                current_process_id = ?, assignee_id = ?, planned_work_date = ?,
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
                payload.current_process_id,
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
            write_card_audit(
                conn,
                card_id,
                user["id"],
                "process_changed",
                {"current_process_id": before["current_process_id"]},
                {"current_process_id": updated_snapshot["current_process_id"]},
            )
        if "assignee_id" in changed:
            write_card_audit(
                conn,
                card_id,
                user["id"],
                "assignee_changed",
                {"assignee_id": before["assignee_id"]},
                {"assignee_id": updated_snapshot["assignee_id"]},
            )
        return updated

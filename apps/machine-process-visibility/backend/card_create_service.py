from __future__ import annotations

from typing import Any

from audit import write_card_audit
from auth import require_admin
from card_update_service import card_change_snapshot
from card_service import get_card_or_404, validate_card_payload
from database import db
from schemas import CardPayload
from utils import now_iso


def create_card_for_user(payload: CardPayload, user: dict[str, Any]) -> dict[str, Any]:
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
                0,
                payload.current_process_id,
                "未着手",
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

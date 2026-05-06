from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException

from audit import write_card_audit
from auth import require_admin
from card_service import get_card_detail_or_404, get_card_or_404
from constants import COMMENT_TYPES
from database import db
from schemas import WorkResultPayload
from utils import now_iso, validate_iso_date


def status_for_completed_qty(completed_qty: int, total_qty: int) -> str:
    if completed_qty >= total_qty:
        return "完了"
    if completed_qty > 0:
        return "作業中"
    return "未着手"


def validate_work_result_payload(payload: WorkResultPayload) -> tuple[str, str, str]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正な作業分類です")

    work_date = validate_iso_date(payload.work_date, "作業日") or date.today().isoformat()
    work_type = payload.comment_type
    comment_body = payload.comment.strip()

    if payload.completed_qty_delta < 0 and work_type != "手戻り":
        raise HTTPException(status_code=400, detail="加工数量のマイナス入力は作業分類が手戻りの場合のみ可能です")
    if work_type == "作業" and (payload.completed_qty_delta <= 0 or payload.work_hours <= 0):
        raise HTTPException(status_code=400, detail="作業の場合は加工数量と作業時間を入力してください")
    if work_type == "手戻り" and (payload.completed_qty_delta >= 0 or not comment_body):
        raise HTTPException(status_code=400, detail="手戻りの場合はマイナスの加工数量と理由コメントを入力してください")
    if work_type == "コメント" and (payload.completed_qty_delta != 0 or payload.work_hours != 0 or not comment_body):
        raise HTTPException(status_code=400, detail="コメントの場合は加工数量と作業時間を0にしてコメントを入力してください")
    if work_type == "開始" and (payload.completed_qty_delta != 0 or payload.work_hours != 0):
        raise HTTPException(status_code=400, detail="開始の場合は加工数量と作業時間を0にしてください")

    return work_date, work_type, comment_body


def register_work_result_for_card(card_id: int, payload: WorkResultPayload, user: dict[str, Any]) -> dict[str, Any]:
    work_date, work_type, comment_body = validate_work_result_payload(payload)
    if payload.assignee_id and payload.assignee_id != user["assignee_id"]:
        require_admin(user)

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        card = get_card_or_404(conn, card_id)
        new_completed = card["completed_qty"] + payload.completed_qty_delta
        if new_completed < 0:
            raise HTTPException(status_code=400, detail="数量増減後の完了数は0未満にできません")
        if new_completed > card["total_qty"]:
            raise HTTPException(status_code=400, detail="数量増減後の完了数は総数を超えられません")

        comment_id = None
        worker_id = payload.assignee_id or user["assignee_id"] or card["assignee_id"]
        if comment_body:
            cur = conn.execute(
                "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (card_id, work_type, comment_body, worker_id, now_iso()),
            )
            comment_id = cur.lastrowid

        conn.execute(
            "UPDATE cards SET completed_qty = ?, status = ?, updated_at = ? WHERE id = ?",
            (new_completed, status_for_completed_qty(new_completed, card["total_qty"]), now_iso(), card_id),
        )
        conn.execute(
            """
            INSERT INTO work_logs(
                card_id, assignee_id, registered_by_user_id, process_id, work_type, work_date,
                completed_qty_delta, work_hours, comment_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                worker_id,
                user["id"],
                card["current_process_id"],
                work_type,
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

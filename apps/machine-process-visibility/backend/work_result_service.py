from __future__ import annotations

import re
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

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
WORK_START_MINUTES = 8 * 60
WORK_END_MINUTES = 22 * 60


def status_for_completed_qty(completed_qty: int, total_qty: int) -> str:
    if completed_qty >= total_qty:
        return "完了"
    if completed_qty > 0:
        return "作業中"
    return "未着手"


def time_to_minutes(value: str, field_name: str) -> int:
    if not TIME_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail=f"{field_name}は HH:MM 形式で入力してください")
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def duration_minutes_from_range(start_time: str | None, end_time: str | None) -> int:
    if not start_time or not end_time:
        raise HTTPException(status_code=400, detail="作業の場合は開始時刻と終了時刻を入力してください")
    start_minutes = time_to_minutes(start_time, "開始時刻")
    end_minutes = time_to_minutes(end_time, "終了時刻")
    if start_minutes < WORK_START_MINUTES or end_minutes > WORK_END_MINUTES:
        raise HTTPException(status_code=400, detail="作業時刻は08:00〜22:00の範囲で入力してください")
    if end_minutes <= start_minutes:
        raise HTTPException(status_code=400, detail="終了時刻は開始時刻より後にしてください")
    return end_minutes - start_minutes


def validate_work_result_payload(payload: WorkResultPayload) -> tuple[str, str, str, int]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正な作業分類です")

    work_date = validate_iso_date(payload.work_date, "作業日") or date.today().isoformat()
    work_type = payload.comment_type
    comment_body = payload.comment.strip()
    records_work_time = work_type in {"作業", "手戻り"}
    duration_minutes = duration_minutes_from_range(payload.start_time, payload.end_time) if records_work_time else 0

    if payload.completed_qty_delta < 0 and work_type != "手戻り":
        raise HTTPException(status_code=400, detail="加工数量のマイナス入力は作業分類が手戻りの場合のみ可能です")
    if work_type == "作業" and payload.completed_qty_delta <= 0:
        raise HTTPException(status_code=400, detail="作業の場合は加工数量を入力してください")
    if work_type == "手戻り" and (payload.completed_qty_delta >= 0 or not comment_body):
        raise HTTPException(status_code=400, detail="手戻りの場合はマイナスの加工数量と理由コメントを入力してください")
    if work_type == "コメント" and (payload.completed_qty_delta != 0 or not comment_body):
        raise HTTPException(status_code=400, detail="コメントの場合は加工数量を0にしてコメントを入力してください")
    if work_type in {"開始", "コメント"} and (payload.start_time or payload.end_time or payload.estimated_minutes):
        raise HTTPException(status_code=400, detail="開始・コメントの場合は作業時刻と見積時間を入力しないでください")
    if work_type == "開始" and payload.completed_qty_delta != 0:
        raise HTTPException(status_code=400, detail="開始の場合は加工数量を0にしてください")

    return work_date, work_type, comment_body, duration_minutes


def register_work_result_for_card(card_id: int, payload: WorkResultPayload, user: dict[str, Any]) -> dict[str, Any]:
    work_date, work_type, comment_body, duration_minutes = validate_work_result_payload(payload)
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
                completed_qty_delta, work_hours, start_time, end_time, duration_minutes, estimated_minutes,
                comment_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                worker_id,
                user["id"],
                card["current_process_id"],
                work_type,
                work_date,
                payload.completed_qty_delta,
                round(duration_minutes / 60, 2),
                payload.start_time,
                payload.end_time,
                duration_minutes,
                payload.estimated_minutes if work_type in {"作業", "手戻り"} else 0,
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

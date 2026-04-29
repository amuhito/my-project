from __future__ import annotations

import csv
from datetime import date
from io import StringIO
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Response

from auth import current_user
from database import db
from utils import escape_csv_cell


router = APIRouter(prefix="/api/reports")


@router.get("/daily")
def daily_report(
    work_date: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    process_id: Optional[int] = Query(None),
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    target_date = work_date or date.today().isoformat()
    where = ["wl.work_date = ?"]
    params: list[Any] = [target_date]
    if assignee_id:
        where.append("wl.assignee_id = ?")
        params.append(assignee_id)
    if process_id:
        where.append("COALESCE(wl.process_id, cards.current_process_id) = ?")
        params.append(process_id)
    with db() as conn:
        return [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                    wl.work_date, wl.completed_qty_delta, wl.work_hours, wl.created_at,
                    cards.order_no, cards.item_type, cards.drawing_no, cards.item_name, cards.remarks,
                    assignees.name AS assignee_name,
                    processes.name AS process_name,
                    comments.body AS comment,
                    comments.comment_type,
                    CASE WHEN comments.comment_type IN ('異常', '気づき') THEN comments.body ELSE '' END AS finding
                FROM work_logs wl
                JOIN cards ON cards.id = wl.card_id
                LEFT JOIN assignees ON assignees.id = wl.assignee_id
                LEFT JOIN processes ON processes.id = COALESCE(wl.process_id, cards.current_process_id)
                LEFT JOIN comments ON comments.id = wl.comment_id
                WHERE {" AND ".join(where)}
                ORDER BY assignees.name, wl.created_at DESC
                """,
                params,
            ).fetchall()
        ]


@router.get("/daily.csv")
def daily_report_csv(
    work_date: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    process_id: Optional[int] = Query(None),
    user: dict[str, Any] = Depends(current_user),
) -> Response:
    rows = daily_report(work_date, assignee_id, process_id)
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "work_date",
            "assignee_name",
            "process_name",
            "order_no",
            "item_type",
            "drawing_no",
            "item_name",
            "remarks",
            "completed_qty_delta",
            "work_hours",
            "comment_type",
            "comment",
            "finding",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows([{key: escape_csv_cell(value) for key, value in row.items()} for row in rows])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="daily_report.csv"'},
    )

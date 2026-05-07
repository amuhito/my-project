from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException

from database import db
from utils import validate_iso_date


def period_range(period: str, base_date: str | None) -> tuple[str, str, str]:
    target = date.fromisoformat(validate_iso_date(base_date, "基準日") or date.today().isoformat())
    if period == "week":
        start = target - timedelta(days=target.weekday())
        end = start + timedelta(days=7)
        label = f"{start.isoformat()}週"
    elif period == "month":
        start = target.replace(day=1)
        end = date(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
        label = f"{start.year}年{start.month}月"
    else:
        raise HTTPException(status_code=400, detail="集計単位は month または week を指定してください")
    return start.isoformat(), end.isoformat(), label


def list_workload(period: str = "month", base_date: str | None = None) -> dict[str, Any]:
    start, end, label = period_range(period, base_date)
    with db() as conn:
        assignees = [dict(row) for row in conn.execute("SELECT * FROM assignees WHERE active = 1 ORDER BY id").fetchall()]
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    wl.id,
                    wl.work_date,
                    wl.work_type,
                    wl.completed_qty_delta,
                    wl.duration_minutes,
                    wl.estimated_minutes,
                    wl.start_time,
                    wl.end_time,
                    wl.assignee_id,
                    a.name AS assignee_name,
                    p.name AS process_name,
                    c.id AS card_id,
                    c.order_no,
                    c.item_type,
                    c.drawing_no,
                    c.item_name,
                    cm.body AS comment_body
                FROM work_logs wl
                JOIN cards c ON c.id = wl.card_id
                LEFT JOIN assignees a ON a.id = wl.assignee_id
                LEFT JOIN processes p ON p.id = COALESCE(wl.process_id, c.current_process_id)
                LEFT JOIN comments cm ON cm.id = wl.comment_id
                WHERE wl.work_date >= ?
                  AND wl.work_date < ?
                  AND wl.work_type IN ('作業', '手戻り')
                ORDER BY wl.work_date DESC, wl.created_at DESC, wl.id DESC
                """,
                (start, end),
            ).fetchall()
        ]

    by_assignee: dict[int, dict[str, Any]] = {
        assignee["id"]: {
            "assignee": assignee,
            "work_count": 0,
            "completed_qty": 0,
            "rework_count": 0,
            "actual_minutes": 0,
            "estimated_minutes": 0,
            "variance_minutes": 0,
            "efficiency_rate": None,
            "processes": {},
            "logs": [],
        }
        for assignee in assignees
    }
    for row in rows:
        assignee_id = row["assignee_id"]
        if assignee_id not in by_assignee:
            continue
        summary = by_assignee[assignee_id]
        actual = int(row["duration_minutes"] or 0)
        estimated = int(row["estimated_minutes"] or 0)
        summary["work_count"] += 1
        summary["completed_qty"] += max(int(row["completed_qty_delta"] or 0), 0)
        summary["rework_count"] += 1 if row["work_type"] == "手戻り" else 0
        summary["actual_minutes"] += actual
        summary["estimated_minutes"] += estimated
        process_name = row["process_name"] or "未設定"
        process_summary = summary["processes"].setdefault(process_name, {"work_count": 0, "actual_minutes": 0, "estimated_minutes": 0})
        process_summary["work_count"] += 1
        process_summary["actual_minutes"] += actual
        process_summary["estimated_minutes"] += estimated
        summary["logs"].append(row)

    summaries = []
    for summary in by_assignee.values():
        summary["variance_minutes"] = summary["estimated_minutes"] - summary["actual_minutes"]
        if summary["estimated_minutes"] > 0:
            summary["efficiency_rate"] = round((summary["actual_minutes"] / summary["estimated_minutes"]) * 100, 1)
        summary["processes"] = [
            {"name": name, **values}
            for name, values in sorted(summary["processes"].items(), key=lambda item: item[0])
        ]
        summaries.append(summary)

    return {
        "period": period,
        "label": label,
        "start_date": start,
        "end_date": (date.fromisoformat(end) - timedelta(days=1)).isoformat(),
        "summaries": summaries,
    }

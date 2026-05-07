from __future__ import annotations

from pathlib import Path
from datetime import date

from dashboard_service import list_workload, period_range


def test_period_range_week_starts_on_monday() -> None:
    start, end, label = period_range("week", "2026-05-07")

    assert start == "2026-05-04"
    assert end == "2026-05-11"
    assert label == "2026-05-04週"


def test_workload_returns_assignee_summaries(initialized_db: Path) -> None:
    result = list_workload(period="month", base_date=date.today().isoformat())

    assert result["period"] == "month"
    assert result["summaries"]
    mitani = next(summary for summary in result["summaries"] if summary["assignee"]["name"] == "三谷")
    assert mitani["work_count"] >= 1
    assert mitani["actual_minutes"] > 0
    assert "variance_minutes" in mitani

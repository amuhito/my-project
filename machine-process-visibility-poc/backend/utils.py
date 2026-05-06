from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from fastapi import HTTPException


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def validate_iso_date(value: Optional[str], field_name: str) -> str | None:
    if value is None:
        return None
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise HTTPException(status_code=400, detail=f"{field_name} は YYYY-MM-DD 形式で指定してください")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} は YYYY-MM-DD 形式で指定してください")
    return value


def escape_csv_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value

from __future__ import annotations

import json
import sqlite3
from typing import Any

from utils import now_iso


def write_card_audit(
    conn: sqlite3.Connection,
    card_id: int,
    user_id: int,
    action: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    conn.execute(
        """
        INSERT INTO card_audit_logs(card_id, user_id, action, before_json, after_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            card_id,
            user_id,
            action,
            json.dumps(before, ensure_ascii=False, sort_keys=True) if before is not None else None,
            json.dumps(after, ensure_ascii=False, sort_keys=True) if after is not None else None,
            now_iso(),
        ),
    )

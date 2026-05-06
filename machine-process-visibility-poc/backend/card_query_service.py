from __future__ import annotations

from typing import Any

from card_service import get_card_detail_or_404, hydrate_card
from database import db


def list_cards_for_user(
    process_id: int | None = None,
    assignee_id: int | None = None,
    tag: str | None = None,
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


def get_card_detail(card_id: int) -> dict[str, Any]:
    with db() as conn:
        return get_card_detail_or_404(conn, card_id)

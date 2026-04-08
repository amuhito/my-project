from __future__ import annotations

import json
from datetime import datetime

from .database import DEFAULT_LIST_TITLES, get_connection
from .schemas import (
    AddCommentRequest,
    BoardResponse,
    CardDetail,
    CreateCardRequest,
    MoveCardRequest,
    SaveCardRequest,
)


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _build_title(project_no: str, customer_name: str, fallback_title: str) -> str:
    project_no = _clean_text(project_no)
    customer_name = _clean_text(customer_name)
    fallback_title = _clean_text(fallback_title)

    if project_no and customer_name:
        return f"{project_no} {customer_name}"
    if project_no:
        return project_no
    if customer_name:
        return customer_name
    return fallback_title or "新規案件"


def _get_list_id_by_title(connection, status: str) -> int | None:
    row = connection.execute(
        "SELECT id FROM board_list WHERE title = ? ORDER BY position ASC LIMIT 1",
        (status,),
    ).fetchone()
    return None if row is None else row["id"]


def fetch_board() -> BoardResponse:
    with get_connection() as connection:
        board_row = connection.execute("SELECT id, title FROM board LIMIT 1").fetchone()
        list_rows = connection.execute(
            "SELECT id, title, position FROM board_list ORDER BY position ASC"
        ).fetchall()

        lists = []
        for list_row in list_rows:
            card_rows = connection.execute(
                """
                SELECT
                    card.id,
                    card.title,
                    card.project_no,
                    card.customer_name,
                    card.received_date,
                    card.requested_due_date,
                    card.assignee_name,
                    card.response_due_date,
                    card.earliest_ship_date,
                    card.notes,
                    card.labels_json,
                    (
                        SELECT COUNT(*)
                        FROM comment
                        WHERE comment.card_id = card.id
                    ) AS comment_count,
                    (
                        SELECT COUNT(*)
                        FROM checklist_item
                        WHERE checklist_item.card_id = card.id
                    ) AS checklist_total,
                    (
                        SELECT COUNT(*)
                        FROM checklist_item
                        WHERE checklist_item.card_id = card.id
                          AND checklist_item.completed = 1
                    ) AS checklist_done
                FROM card
                WHERE card.list_id = ?
                ORDER BY card.position ASC
                """,
                (list_row["id"],),
            ).fetchall()

            cards = []
            for row in card_rows:
                total = row["checklist_total"] or 0
                done = row["checklist_done"] or 0
                cards.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "project_no": row["project_no"] or "",
                        "customer_name": row["customer_name"] or row["title"],
                        "status": list_row["title"],
                        "received_date": row["received_date"],
                        "labels": json.loads(row["labels_json"]),
                        "requested_due_date": row["requested_due_date"],
                        "assignee_name": row["assignee_name"] or "",
                        "response_due_date": row["response_due_date"],
                        "earliest_ship_date": row["earliest_ship_date"],
                        "notes": row["notes"] or "",
                        "checklist_progress": f"{done}/{total}",
                        "comment_count": row["comment_count"],
                    }
                )

            lists.append(
                {
                    "id": list_row["id"],
                    "title": list_row["title"],
                    "position": list_row["position"],
                    "cards": cards,
                }
            )

        return BoardResponse(id=board_row["id"], title=board_row["title"], lists=lists)


def fetch_card_detail(card_id: int) -> CardDetail | None:
    with get_connection() as connection:
        card_row = connection.execute(
            """
            SELECT
                card.id,
                card.list_id,
                card.title,
                card.project_no,
                card.customer_name,
                card.received_date,
                card.requested_due_date,
                card.assignee_name,
                card.response_due_date,
                card.earliest_ship_date,
                card.description,
                card.notes,
                card.history_text,
                card.labels_json,
                board_list.title AS status
            FROM card
            JOIN board_list ON board_list.id = card.list_id
            WHERE card.id = ?
            """,
            (card_id,),
        ).fetchone()
        if card_row is None:
            return None

        comment_rows = connection.execute(
            "SELECT id, author, body, created_at FROM comment WHERE card_id = ? ORDER BY id ASC",
            (card_id,),
        ).fetchall()
        checklist_rows = connection.execute(
            """
            SELECT id, text, completed, position
            FROM checklist_item
            WHERE card_id = ?
            ORDER BY position ASC, id ASC
            """,
            (card_id,),
        ).fetchall()
        activity_rows = connection.execute(
            "SELECT id, message, created_at FROM activity WHERE card_id = ? ORDER BY id DESC",
            (card_id,),
        ).fetchall()

        return CardDetail(
            id=card_row["id"],
            list_id=card_row["list_id"],
            title=card_row["title"],
            project_no=card_row["project_no"] or "",
            customer_name=card_row["customer_name"] or "",
            status=card_row["status"],
            received_date=card_row["received_date"],
            requested_due_date=card_row["requested_due_date"],
            assignee_name=card_row["assignee_name"] or "",
            response_due_date=card_row["response_due_date"],
            earliest_ship_date=card_row["earliest_ship_date"],
            description=card_row["description"],
            notes=card_row["notes"] or "",
            history_text=card_row["history_text"] or "",
            labels=json.loads(card_row["labels_json"]),
            comments=[
                {
                    "id": row["id"],
                    "author": row["author"],
                    "body": row["body"],
                    "created_at": row["created_at"],
                }
                for row in comment_rows
            ],
            checklist=[
                {
                    "id": row["id"],
                    "text": row["text"],
                    "completed": bool(row["completed"]),
                    "position": row["position"],
                }
                for row in checklist_rows
            ],
            activities=[
                {
                    "id": row["id"],
                    "message": row["message"],
                    "created_at": row["created_at"],
                }
                for row in activity_rows
            ],
        )


def move_card(payload: MoveCardRequest) -> None:
    with get_connection() as connection:
        card_row = connection.execute("SELECT id FROM card WHERE id = ?", (payload.card_id,)).fetchone()
        if card_row is None:
            raise ValueError("Card not found")

        source_cards = connection.execute(
            "SELECT id FROM card WHERE list_id = ? ORDER BY position ASC",
            (payload.source_list_id,),
        ).fetchall()
        source_ids = [row["id"] for row in source_cards if row["id"] != payload.card_id]

        for index, source_card_id in enumerate(source_ids):
            connection.execute("UPDATE card SET position = ? WHERE id = ?", (index, source_card_id))

        destination_cards = connection.execute(
            "SELECT id FROM card WHERE list_id = ? ORDER BY position ASC",
            (payload.destination_list_id,),
        ).fetchall()
        destination_ids = [row["id"] for row in destination_cards if row["id"] != payload.card_id]
        destination_index = min(payload.destination_index, len(destination_ids))
        destination_ids.insert(destination_index, payload.card_id)

        for index, destination_card_id in enumerate(destination_ids):
            connection.execute(
                "UPDATE card SET list_id = ?, position = ? WHERE id = ?",
                (payload.destination_list_id, index, destination_card_id),
            )

        destination_title = connection.execute(
            "SELECT title FROM board_list WHERE id = ?",
            (payload.destination_list_id,),
        ).fetchone()["title"]
        connection.execute(
            "INSERT INTO activity (card_id, message, created_at) VALUES (?, ?, ?)",
            (payload.card_id, f"「{destination_title}」に移動しました", _now_text()),
        )


def save_card(card_id: int, payload: SaveCardRequest) -> CardDetail | None:
    with get_connection() as connection:
        current = connection.execute(
            """
            SELECT
                card.list_id,
                card.title,
                card.project_no,
                card.customer_name,
                card.received_date,
                card.requested_due_date,
                card.assignee_name,
                card.response_due_date,
                card.earliest_ship_date,
                card.description,
                card.notes,
                card.history_text,
                card.labels_json,
                board_list.title AS status
            FROM card
            JOIN board_list ON board_list.id = card.list_id
            WHERE card.id = ?
            """,
            (card_id,),
        ).fetchone()
        if current is None:
            return None

        destination_status = payload.status if payload.status in DEFAULT_LIST_TITLES else current["status"]
        destination_list_id = _get_list_id_by_title(connection, destination_status)
        if destination_list_id is None:
            destination_list_id = current["list_id"]

        target_position = connection.execute(
            "SELECT position FROM card WHERE id = ?",
            (card_id,),
        ).fetchone()["position"]
        if destination_list_id != current["list_id"]:
            source_cards = connection.execute(
                "SELECT id FROM card WHERE list_id = ? AND id != ? ORDER BY position ASC",
                (current["list_id"], card_id),
            ).fetchall()
            for index, source_card in enumerate(source_cards):
                connection.execute(
                    "UPDATE card SET position = ? WHERE id = ?",
                    (index, source_card["id"]),
                )

            target_position = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM card WHERE list_id = ?",
                (destination_list_id,),
            ).fetchone()[0]

        next_title = _build_title(payload.project_no, payload.customer_name, payload.title)
        connection.execute(
            """
            UPDATE card
            SET
                list_id = ?,
                position = ?,
                title = ?,
                project_no = ?,
                customer_name = ?,
                received_date = ?,
                requested_due_date = ?,
                assignee_name = ?,
                response_due_date = ?,
                earliest_ship_date = ?,
                description = ?,
                notes = ?,
                history_text = ?,
                labels_json = ?
            WHERE id = ?
            """,
            (
                destination_list_id,
                target_position,
                next_title,
                _clean_text(payload.project_no),
                _clean_text(payload.customer_name),
                payload.received_date or None,
                payload.requested_due_date or None,
                _clean_text(payload.assignee_name),
                payload.response_due_date or None,
                payload.earliest_ship_date or None,
                _clean_text(payload.description),
                _clean_text(payload.notes),
                _clean_text(payload.history_text),
                json.dumps(payload.labels, ensure_ascii=False),
                card_id,
            ),
        )

        existing_items = connection.execute(
            "SELECT id FROM checklist_item WHERE card_id = ?",
            (card_id,),
        ).fetchall()
        existing_ids = {row["id"] for row in existing_items}
        received_ids = {item.id for item in payload.checklist if item.id is not None}

        for item_id in existing_ids - received_ids:
            connection.execute("DELETE FROM checklist_item WHERE id = ?", (item_id,))

        for item in payload.checklist:
            if item.id is None:
                connection.execute(
                    """
                    INSERT INTO checklist_item (card_id, text, completed, position)
                    VALUES (?, ?, ?, ?)
                    """,
                    (card_id, item.text.strip(), int(item.completed), item.position),
                )
            else:
                connection.execute(
                    """
                    UPDATE checklist_item
                    SET text = ?, completed = ?, position = ?
                    WHERE id = ? AND card_id = ?
                    """,
                    (item.text.strip(), int(item.completed), item.position, item.id, card_id),
                )

        messages = []
        if current["status"] != destination_status:
            messages.append(f"ステータスを「{destination_status}」に更新しました")
        if current["project_no"] != _clean_text(payload.project_no):
            messages.append("受注番号を更新しました")
        if current["customer_name"] != _clean_text(payload.customer_name):
            messages.append("ユーザー名を更新しました")
        if (current["response_due_date"] or None) != (payload.response_due_date or None):
            messages.append("回答納期を更新しました")
        if (current["earliest_ship_date"] or None) != (payload.earliest_ship_date or None):
            messages.append("最短発送日を更新しました")
        if current["notes"] != _clean_text(payload.notes):
            messages.append("備考を更新しました")
        messages.append("チェックリストを保存しました")

        for message in dict.fromkeys(messages):
            connection.execute(
                "INSERT INTO activity (card_id, message, created_at) VALUES (?, ?, ?)",
                (card_id, message, _now_text()),
            )

    return fetch_card_detail(card_id)


def add_comment(card_id: int, payload: AddCommentRequest) -> CardDetail | None:
    with get_connection() as connection:
        exists = connection.execute("SELECT 1 FROM card WHERE id = ?", (card_id,)).fetchone()
        if exists is None:
            return None

        connection.execute(
            "INSERT INTO comment (card_id, author, body, created_at) VALUES (?, ?, ?, ?)",
            (card_id, payload.author.strip() or "あなた", payload.body.strip(), _now_text()),
        )
        connection.execute(
            "INSERT INTO activity (card_id, message, created_at) VALUES (?, ?, ?)",
            (card_id, "コメントを追加しました", _now_text()),
        )

    return fetch_card_detail(card_id)


def create_card(list_id: int, payload: CreateCardRequest) -> CardDetail | None:
    with get_connection() as connection:
        list_row = connection.execute(
            "SELECT title FROM board_list WHERE id = ?",
            (list_id,),
        ).fetchone()
        if list_row is None:
            return None

        next_position = connection.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM card WHERE list_id = ?",
            (list_id,),
        ).fetchone()[0]
        title = _build_title(payload.project_no, payload.customer_name, payload.title)

        cursor = connection.execute(
            """
            INSERT INTO card (
                list_id,
                title,
                description,
                labels_json,
                position,
                project_no,
                customer_name,
                notes,
                history_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                list_id,
                title,
                _clean_text(payload.description),
                "[]",
                next_position,
                _clean_text(payload.project_no),
                _clean_text(payload.customer_name),
                "",
                "",
            ),
        )
        card_id = cursor.lastrowid

        connection.execute(
            "INSERT INTO activity (card_id, message, created_at) VALUES (?, ?, ?)",
            (card_id, f"「{list_row['title']}」にカードを作成しました", _now_text()),
        )

    return fetch_card_detail(card_id)

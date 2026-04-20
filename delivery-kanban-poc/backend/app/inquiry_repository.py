from __future__ import annotations

import re
from datetime import UTC, datetime

from .auth import AuthUser
from .database import PROCESS_COLUMNS, get_connection
from .schemas import (
    CreateInquiryRequest,
    InquiryDetail,
    InquiryItemDetail,
    InquiryItemSummary,
    InquiryListResponse,
    InquiryMoveRequest,
    InquirySummary,
    KanbanColumn,
    KanbanResponse,
    UpdateInquiryItemRequest,
)

PROCESS_ORDER = [column[0] for column in PROCESS_COLUMNS]
PROCESS_LABELS = {column[0]: column[1] for column in PROCESS_COLUMNS}
STATE_LABELS = {
    "normal": "通常",
    "waiting": "待ち",
    "done": "完了",
}
REQUEST_KIND_LABELS = {
    "confirm": "納期確認",
    "shorten": "納期短縮",
}


def _now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _validate_process(process: str) -> str:
    if process not in PROCESS_LABELS:
        raise ValueError("不正な工程です。")
    return process


def _validate_state(state: str) -> str:
    if state not in STATE_LABELS:
        raise ValueError("不正な状態です。")
    return state


def _parse_range_token(token: str) -> list[str] | None:
    matched = re.fullmatch(r"([PES])\s*-\s*(\d+)\s*[~〜～]\s*(\d+)", token, re.IGNORECASE)
    if not matched:
        return None

    prefix = matched.group(1).upper()
    start_text = matched.group(2)
    end_text = matched.group(3)

    if len(end_text) < len(start_text):
        end_text = start_text[: len(start_text) - len(end_text)] + end_text

    start_no = int(start_text)
    end_no = int(end_text)
    if end_no < start_no:
        raise ValueError(f"範囲指定が不正です: {token}")

    width = len(start_text)
    return [f"{prefix}-{number:0{width}d}" for number in range(start_no, end_no + 1)]


def parse_order_numbers(raw_text: str) -> list[str]:
    text = raw_text.strip()
    if not text:
        raise ValueError("受注Noを入力してください。")

    tokens = [part.strip() for part in re.split(r"[\n,、]+", text) if part.strip()]
    if not tokens:
        raise ValueError("受注Noを入力してください。")

    parsed: list[str] = []
    invalid_tokens: list[str] = []

    for token in tokens:
        ranged = _parse_range_token(token)
        if ranged is not None:
            parsed.extend(ranged)
            continue

        matched = re.fullmatch(r"([PES])\s*-\s*(\d+)", token, re.IGNORECASE)
        if matched is None:
            invalid_tokens.append(token)
            continue
        parsed.append(f"{matched.group(1).upper()}-{matched.group(2)}")

    if invalid_tokens:
        raise ValueError("受注No形式が不正です: " + ", ".join(invalid_tokens))

    # 順序を保って重複を除去
    unique_items: list[str] = []
    seen = set()
    for item in parsed:
        if item in seen:
            continue
        seen.add(item)
        unique_items.append(item)

    return unique_items


def _next_process_position(connection, process: str) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM inquiry_item WHERE process = ?",
        (process,),
    ).fetchone()
    return int(row["next_position"])


def _reindex_process(connection, process: str) -> None:
    rows = connection.execute(
        "SELECT id FROM inquiry_item WHERE process = ? ORDER BY position ASC, id ASC",
        (process,),
    ).fetchall()
    for index, row in enumerate(rows):
        connection.execute("UPDATE inquiry_item SET position = ? WHERE id = ?", (index, row["id"]))


def _format_requested_due(inquiry: dict) -> str:
    if inquiry["requested_due_type"] == "shortest":
        return "最短"
    return inquiry["requested_due_date"] or "-"


def _row_to_item_summary(row) -> InquiryItemSummary:
    inquiry_id = row["inquiry_id"]
    return InquiryItemSummary(
        id=row["id"],
        inquiry_id=inquiry_id,
        inquiry_display_id=f"INQ-{inquiry_id:05d}",
        item_type=row["item_type"],
        item_no=row["item_no"],
        process=row["process"],
        process_label=PROCESS_LABELS[row["process"]],
        owner=row["owner"] or "",
        state=row["state"],
        state_label=STATE_LABELS[row["state"]],
        planned_arrival_date=row["planned_arrival_date"],
        actual_arrival_date=row["actual_arrival_date"],
        packing_due_date=row["packing_due_date"],
        confirmed_shipping_date=row["confirmed_shipping_date"],
        drawing_ready_confirmed=bool(row["drawing_ready_confirmed"]),
        drawing_ready_confirmed_at=row["drawing_ready_confirmed_at"],
        updated_at=row["updated_at"],
        remarks=row["remarks"],
        customer_name=row["customer_name"],
        request_kind=row["request_kind"],
        request_kind_label=REQUEST_KIND_LABELS[row["request_kind"]],
        requested_due_type=row["requested_due_type"],
        requested_due_date=row["requested_due_date"],
        requested_due_display=("最短" if row["requested_due_type"] == "shortest" else (row["requested_due_date"] or "-")),
    )


def fetch_inquiry_list() -> InquiryListResponse:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                inquiry.id,
                inquiry.customer_name,
                inquiry.requested_due_type,
                inquiry.requested_due_date,
                inquiry.request_kind,
                inquiry.remarks,
                inquiry.created_at,
                inquiry.updated_at,
                COUNT(inquiry_item.id) AS item_count
            FROM inquiry
            LEFT JOIN inquiry_item ON inquiry_item.inquiry_id = inquiry.id
            GROUP BY inquiry.id
            ORDER BY inquiry.id DESC
            """
        ).fetchall()

    inquiries = [
        InquirySummary(
            id=row["id"],
            display_id=f"INQ-{row['id']:05d}",
            customer_name=row["customer_name"],
            requested_due_type=row["requested_due_type"],
            requested_due_date=row["requested_due_date"],
            requested_due_display=("最短" if row["requested_due_type"] == "shortest" else (row["requested_due_date"] or "-")),
            request_kind=row["request_kind"],
            request_kind_label=REQUEST_KIND_LABELS[row["request_kind"]],
            remarks=row["remarks"],
            item_count=row["item_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
    return InquiryListResponse(inquiries=inquiries)


def fetch_inquiry_detail(inquiry_id: int) -> InquiryDetail | None:
    with get_connection() as connection:
        inquiry = connection.execute(
            """
            SELECT
                id,
                customer_name,
                requested_due_type,
                requested_due_date,
                request_kind,
                remarks,
                created_at,
                updated_at
            FROM inquiry
            WHERE id = ?
            """,
            (inquiry_id,),
        ).fetchone()
        if inquiry is None:
            return None

        item_rows = connection.execute(
            """
            SELECT
                inquiry_item.*,
                inquiry.customer_name,
                inquiry.request_kind,
                inquiry.requested_due_type,
                inquiry.requested_due_date
            FROM inquiry_item
            JOIN inquiry ON inquiry.id = inquiry_item.inquiry_id
            WHERE inquiry_item.inquiry_id = ?
            ORDER BY inquiry_item.item_type ASC, inquiry_item.item_no ASC, inquiry_item.id ASC
            """,
            (inquiry_id,),
        ).fetchall()

    items = [_row_to_item_summary(row) for row in item_rows]
    return InquiryDetail(
        id=inquiry["id"],
        display_id=f"INQ-{inquiry['id']:05d}",
        customer_name=inquiry["customer_name"],
        requested_due_type=inquiry["requested_due_type"],
        requested_due_date=inquiry["requested_due_date"],
        requested_due_display=_format_requested_due(inquiry),
        request_kind=inquiry["request_kind"],
        request_kind_label=REQUEST_KIND_LABELS[inquiry["request_kind"]],
        remarks=inquiry["remarks"],
        created_at=inquiry["created_at"],
        updated_at=inquiry["updated_at"],
        items=items,
    )


def create_inquiry(payload: CreateInquiryRequest, actor: AuthUser) -> InquiryDetail:
    customer_name = _normalize_text(payload.customer_name)
    if not customer_name:
        raise ValueError("納入先は必須です。")

    if payload.requested_due_type not in {"shortest", "specific"}:
        raise ValueError("希望納期種別が不正です。")

    requested_due_date = payload.requested_due_date
    if payload.requested_due_type == "specific" and not requested_due_date:
        raise ValueError("希望納期種別が指定日の場合、日付は必須です。")

    if payload.requested_due_type == "shortest":
        requested_due_date = None

    if payload.request_kind not in {"confirm", "shorten"}:
        raise ValueError("依頼内容が不正です。")

    item_numbers = parse_order_numbers(payload.order_nos)
    now_text = _now_text()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO inquiry (
                customer_name,
                requested_due_type,
                requested_due_date,
                request_kind,
                remarks,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_name,
                payload.requested_due_type,
                requested_due_date,
                payload.request_kind,
                _normalize_text(payload.remarks) or None,
                now_text,
                now_text,
            ),
        )
        inquiry_id = cursor.lastrowid

        for item_no in item_numbers:
            item_type = item_no.split("-", 1)[0].upper()
            connection.execute(
                """
                INSERT INTO inquiry_item (
                    inquiry_id,
                    item_type,
                    item_no,
                    process,
                    owner,
                    state,
                    planned_arrival_date,
                    actual_arrival_date,
                    packing_due_date,
                    confirmed_shipping_date,
                    drawing_ready_confirmed,
                    drawing_ready_confirmed_at,
                    updated_at,
                    remarks,
                    position
                )
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, 0, NULL, ?, NULL, ?)
                """,
                (
                    inquiry_id,
                    item_type,
                    item_no,
                    "not_drawn",
                    "",
                    "waiting",
                    now_text,
                    _next_process_position(connection, "not_drawn"),
                ),
            )

        connection.execute(
            "UPDATE inquiry SET updated_at = ? WHERE id = ?",
            (now_text, inquiry_id),
        )
        _ = actor

    detail = fetch_inquiry_detail(inquiry_id)
    if detail is None:
        raise ValueError("問い合わせ作成後の取得に失敗しました。")
    return detail


def fetch_kanban() -> KanbanResponse:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                inquiry_item.*,
                inquiry.customer_name,
                inquiry.request_kind,
                inquiry.requested_due_type,
                inquiry.requested_due_date
            FROM inquiry_item
            JOIN inquiry ON inquiry.id = inquiry_item.inquiry_id
            ORDER BY inquiry_item.process ASC, inquiry_item.position ASC, inquiry_item.id ASC
            """
        ).fetchall()

    grouped: dict[str, list[InquiryItemSummary]] = {process: [] for process in PROCESS_ORDER}
    for row in rows:
        process = row["process"]
        if process not in grouped:
            continue
        grouped[process].append(_row_to_item_summary(row))

    columns = [
        KanbanColumn(process=process, label=PROCESS_LABELS[process], items=grouped[process])
        for process in PROCESS_ORDER
    ]
    return KanbanResponse(columns=columns)


def fetch_inquiry_item(item_id: int) -> InquiryItemDetail | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                inquiry_item.*,
                inquiry.customer_name,
                inquiry.request_kind,
                inquiry.requested_due_type,
                inquiry.requested_due_date
            FROM inquiry_item
            JOIN inquiry ON inquiry.id = inquiry_item.inquiry_id
            WHERE inquiry_item.id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None

    summary = _row_to_item_summary(row)
    return InquiryItemDetail(**summary.model_dump())


def update_inquiry_item(item_id: int, payload: UpdateInquiryItemRequest, actor: AuthUser) -> InquiryItemDetail | None:
    _validate_process(payload.process)
    _validate_state(payload.state)
    now_text = _now_text()

    with get_connection() as connection:
        current = connection.execute(
            "SELECT id, inquiry_id, process, position FROM inquiry_item WHERE id = ?",
            (item_id,),
        ).fetchone()
        if current is None:
            return None

        new_position = current["position"]
        if payload.process != current["process"]:
            new_position = _next_process_position(connection, payload.process)

        connection.execute(
            """
            UPDATE inquiry_item
            SET
                process = ?,
                owner = ?,
                state = ?,
                planned_arrival_date = ?,
                actual_arrival_date = ?,
                packing_due_date = ?,
                confirmed_shipping_date = ?,
                updated_at = ?,
                remarks = ?,
                position = ?
            WHERE id = ?
            """,
            (
                payload.process,
                _normalize_text(payload.owner),
                payload.state,
                payload.planned_arrival_date,
                payload.actual_arrival_date,
                payload.packing_due_date,
                payload.confirmed_shipping_date,
                now_text,
                _normalize_text(payload.remarks) or None,
                int(new_position),
                item_id,
            ),
        )

        if payload.process != current["process"]:
            _reindex_process(connection, current["process"])
            _reindex_process(connection, payload.process)

        connection.execute(
            "UPDATE inquiry SET updated_at = ? WHERE id = ?",
            (now_text, current["inquiry_id"]),
        )

    return fetch_inquiry_item(item_id)


def move_inquiry_item(payload: InquiryMoveRequest, actor: AuthUser) -> KanbanResponse:
    _validate_process(payload.destination_process)

    with get_connection() as connection:
        current = connection.execute(
            "SELECT id, inquiry_id, process FROM inquiry_item WHERE id = ?",
            (payload.item_id,),
        ).fetchone()
        if current is None:
            raise ValueError("対象の子案件が見つかりません。")

        source_process = current["process"]
        destination_process = payload.destination_process

        source_ids = [
            row["id"]
            for row in connection.execute(
                "SELECT id FROM inquiry_item WHERE process = ? ORDER BY position ASC, id ASC",
                (source_process,),
            ).fetchall()
            if row["id"] != payload.item_id
        ]
        for index, current_id in enumerate(source_ids):
            connection.execute("UPDATE inquiry_item SET position = ? WHERE id = ?", (index, current_id))

        destination_ids = [
            row["id"]
            for row in connection.execute(
                "SELECT id FROM inquiry_item WHERE process = ? ORDER BY position ASC, id ASC",
                (destination_process,),
            ).fetchall()
            if row["id"] != payload.item_id
        ]
        insert_index = min(max(payload.destination_index, 0), len(destination_ids))
        destination_ids.insert(insert_index, payload.item_id)

        now_text = _now_text()
        for index, current_id in enumerate(destination_ids):
            connection.execute(
                "UPDATE inquiry_item SET process = ?, position = ?, updated_at = ? WHERE id = ?",
                (destination_process, index, now_text, current_id),
            )

        connection.execute(
            "UPDATE inquiry SET updated_at = ? WHERE id = ?",
            (now_text, current["inquiry_id"]),
        )

    return fetch_kanban()


def confirm_drawing_ready(item_id: int, actor: AuthUser) -> InquiryItemDetail | None:
    now_text = _now_text()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, inquiry_id, process FROM inquiry_item WHERE id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            return None

        previous_process = row["process"]
        next_process = "arranging"
        next_position = _next_process_position(connection, next_process)

        connection.execute(
            """
            UPDATE inquiry_item
            SET
                drawing_ready_confirmed = 1,
                drawing_ready_confirmed_at = ?,
                process = ?,
                position = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now_text, next_process, next_position, now_text, item_id),
        )

        if previous_process != next_process:
            _reindex_process(connection, previous_process)
            _reindex_process(connection, next_process)

        connection.execute(
            "UPDATE inquiry SET updated_at = ? WHERE id = ?",
            (now_text, row["inquiry_id"]),
        )

    return fetch_inquiry_item(item_id)

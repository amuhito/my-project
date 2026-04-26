from __future__ import annotations

import csv
import hashlib
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


DB_PATH = Path(__file__).with_name("machine_poc.sqlite3")
DESCRIPTION_TEMPLATE = "【状態】\n\n【注意】\n\n【次工程】\n"
PROCESSES = ["未振り分け", "内面研磨", "刃物研磨", "機械加工", "板金加工", "手加工", "完了"]
COMMENT_TYPES = {"作業", "気づき", "異常", "補足"}
DEFAULT_PASSWORD = "password"
ORDER_NO_PATTERN = re.compile(r"^[A-Z]-\d{5}$")
ITEM_TYPE_PATTERN = re.compile(r"^\d{2}$")


app = FastAPI(title="機械課 工程見える化PoC")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


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


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def table_has_rows(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(f"SELECT EXISTS(SELECT 1 FROM {table})").fetchone()[0] == 1


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def sync_process_master(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT 1 FROM processes WHERE name = '未着手'").fetchone() and not conn.execute(
        "SELECT 1 FROM processes WHERE name = '未振り分け'"
    ).fetchone():
        conn.execute("UPDATE processes SET name = '未振り分け' WHERE name = '未着手'")

    for sort_order, name in enumerate(PROCESSES, start=1):
        row = conn.execute("SELECT id FROM processes WHERE name = ?", (name,)).fetchone()
        if row:
            conn.execute("UPDATE processes SET sort_order = ?, active = 1 WHERE id = ?", (sort_order, row["id"]))
        else:
            conn.execute("INSERT INTO processes(name, sort_order, active) VALUES (?, ?, 1)", (name, sort_order))

    machine_process_id = conn.execute("SELECT id FROM processes WHERE name = '機械加工'").fetchone()["id"]
    old_machine_rows = conn.execute("SELECT id FROM processes WHERE name IN ('マシニング', 'ワイヤー')").fetchall()
    for row in old_machine_rows:
        conn.execute("UPDATE cards SET current_process_id = ? WHERE current_process_id = ?", (machine_process_id, row["id"]))
        conn.execute("DELETE FROM processes WHERE id = ?", (row["id"],))

    conn.execute(
        "UPDATE processes SET active = 0 WHERE name NOT IN (?, ?, ?, ?, ?, ?, ?)",
        PROCESSES,
    )


def sync_seed_card_metadata(conn: sqlite3.Connection) -> None:
    seed_metadata = {
        "SH-208500L2": ("ORD-2026-001", "加工品", "内面研磨優先"),
        "HB-110470": ("ORD-2026-002", "刃物", ""),
        "RW-001": ("ORD-2026-003", "追加工", "外注戻り後の追加工"),
    }
    for drawing_no, (order_no, item_type, remarks) in seed_metadata.items():
        conn.execute(
            """
            UPDATE cards
            SET order_no = CASE WHEN order_no = '' THEN ? ELSE order_no END,
                item_type = CASE WHEN item_type = '' THEN ? ELSE item_type END,
                remarks = CASE WHEN remarks = '' THEN ? ELSE remarks END
            WHERE drawing_no = ?
            """,
            (order_no, item_type, remarks, drawing_no),
        )


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS assignees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT NOT NULL DEFAULT '',
                item_type TEXT NOT NULL DEFAULT '',
                drawing_no TEXT NOT NULL,
                item_name TEXT NOT NULL,
                remarks TEXT NOT NULL DEFAULT '',
                total_qty INTEGER NOT NULL CHECK(total_qty >= 0),
                completed_qty INTEGER NOT NULL DEFAULT 0 CHECK(completed_qty >= 0),
                current_process_id INTEGER NOT NULL REFERENCES processes(id),
                status TEXT NOT NULL CHECK(status IN ('未着手', '作業中', '完了')),
                assignee_id INTEGER REFERENCES assignees(id),
                planned_work_date TEXT,
                due_date TEXT,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK(completed_qty <= total_qty)
            );
            CREATE TABLE IF NOT EXISTS card_tags (
                card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY(card_id, tag_id)
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                comment_type TEXT NOT NULL CHECK(comment_type IN ('作業', '気づき', '異常', '補足')),
                body TEXT NOT NULL,
                user_id INTEGER REFERENCES assignees(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                assignee_id INTEGER REFERENCES assignees(id),
                process_id INTEGER REFERENCES processes(id),
                work_date TEXT NOT NULL,
                completed_qty_delta INTEGER NOT NULL CHECK(completed_qty_delta >= 0),
                work_hours REAL NOT NULL CHECK(work_hours >= 0),
                comment_id INTEGER REFERENCES comments(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                assignee_id INTEGER REFERENCES assignees(id),
                role TEXT NOT NULL DEFAULT 'operator',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL
            );
            """
        )

        ensure_column(conn, "cards", "order_no", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "cards", "item_type", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "cards", "remarks", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "work_logs", "process_id", "INTEGER REFERENCES processes(id)")
        sync_seed_card_metadata(conn)

        if not table_has_rows(conn, "processes"):
            conn.executemany(
                "INSERT INTO processes(name, sort_order, active) VALUES (?, ?, 1)",
                [(name, i + 1) for i, name in enumerate(PROCESSES)],
            )

        sync_process_master(conn)

        if not table_has_rows(conn, "assignees"):
            conn.executemany(
                "INSERT INTO assignees(name, color, active) VALUES (?, ?, ?)",
                [
                    ("三谷", "#2563eb", 1),
                    ("山本", "#16a34a", 1),
                    ("佐藤", "#dc2626", 1),
                    ("田中", "#9333ea", 1),
                    ("鈴木", "#ea580c", 1),
                ],
            )

        if not table_has_rows(conn, "tags"):
            conn.executemany(
                "INSERT INTO tags(name, color) VALUES (?, ?)",
                [
                    ("追加工", "#e11d48"),
                    ("至急", "#f97316"),
                    ("厳守", "#7c3aed"),
                    ("外注戻り", "#0891b2"),
                    ("要確認", "#ca8a04"),
                ],
            )

        if not table_has_rows(conn, "cards"):
            today = date.today()
            seed_cards = [
                ("ORD-2026-001", "加工品", "SH-208500L2", "シュート", "内面研磨優先", 61, 15, "内面研磨", "作業中", "三谷", today, today + timedelta(days=5), ["至急"]),
                ("ORD-2026-002", "刃物", "HB-110470", "平刃", "", 8, 0, "刃物研磨", "未着手", "山本", today + timedelta(days=1), today + timedelta(days=7), ["厳守"]),
                ("ORD-2026-003", "追加工", "RW-001", "外注戻り追加工品", "外注戻り後の追加工", 3, 0, "機械加工", "未着手", "佐藤", today + timedelta(days=2), today + timedelta(days=4), ["追加工", "外注戻り"]),
            ]
            for order_no, item_type, drawing_no, item_name, remarks, total, done, process, status, assignee, planned, due, tag_names in seed_cards:
                process_id = conn.execute("SELECT id FROM processes WHERE name = ?", (process,)).fetchone()["id"]
                assignee_id = conn.execute("SELECT id FROM assignees WHERE name = ?", (assignee,)).fetchone()["id"]
                cur = conn.execute(
                    """
                    INSERT INTO cards(
                        order_no, item_type, drawing_no, item_name, remarks,
                        total_qty, completed_qty, current_process_id, status,
                        assignee_id, planned_work_date, due_date, description, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_no,
                        item_type,
                        drawing_no,
                        item_name,
                        remarks,
                        total,
                        done,
                        process_id,
                        status,
                        assignee_id,
                        planned.isoformat(),
                        due.isoformat(),
                        DESCRIPTION_TEMPLATE,
                        now_iso(),
                        now_iso(),
                    ),
                )
                card_id = cur.lastrowid
                for tag_name in tag_names:
                    tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()["id"]
                    conn.execute("INSERT INTO card_tags(card_id, tag_id) VALUES (?, ?)", (card_id, tag_id))

        if not table_has_rows(conn, "users"):
            assignees = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM assignees").fetchall()}
            users = [
                ("admin", "管理者", hash_password("admin123"), None, "admin", 1, now_iso()),
                ("mitani", "三谷", hash_password(DEFAULT_PASSWORD), assignees.get("三谷"), "operator", 1, now_iso()),
                ("yamamoto", "山本", hash_password(DEFAULT_PASSWORD), assignees.get("山本"), "operator", 1, now_iso()),
                ("sato", "佐藤", hash_password(DEFAULT_PASSWORD), assignees.get("佐藤"), "operator", 1, now_iso()),
                ("tanaka", "田中", hash_password(DEFAULT_PASSWORD), assignees.get("田中"), "operator", 1, now_iso()),
                ("suzuki", "鈴木", hash_password(DEFAULT_PASSWORD), assignees.get("鈴木"), "operator", 1, now_iso()),
            ]
            conn.executemany(
                """
                INSERT INTO users(username, display_name, password_hash, assignee_id, role, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                users,
            )


class CardPayload(BaseModel):
    order_no: str = ""
    item_type: str = ""
    drawing_no: str
    item_name: str
    remarks: str = ""
    total_qty: int = Field(ge=0)
    completed_qty: int = Field(ge=0)
    current_process_id: int
    status: str
    assignee_id: Optional[int] = None
    planned_work_date: Optional[str] = None
    due_date: Optional[str] = None
    description: str = DESCRIPTION_TEMPLATE
    tag_ids: list[int] = []


class CommentPayload(BaseModel):
    comment_type: str
    body: str
    user_id: Optional[int] = None


class WorkResultPayload(BaseModel):
    completed_qty_delta: int = Field(ge=0)
    work_hours: float = Field(ge=0)
    assignee_id: Optional[int] = None
    work_date: Optional[str] = None
    comment_type: str = "作業"
    comment: str = ""


class LoginPayload(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def public_user(conn: sqlite3.Connection, user: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    user_dict = dict(user)
    assignee = None
    if user_dict["assignee_id"]:
        assignee = row_to_dict(conn.execute("SELECT * FROM assignees WHERE id = ?", (user_dict["assignee_id"],)).fetchone())
    return {
        "id": user_dict["id"],
        "username": user_dict["username"],
        "display_name": user_dict["display_name"],
        "assignee_id": user_dict["assignee_id"],
        "assignee": assignee,
        "role": user_dict["role"],
    }


def current_user(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="ログインしてください")
    token = authorization.removeprefix("Bearer ").strip()
    with db() as conn:
        row = conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND users.active = 1
            """,
            (token,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="ログインしてください")
        return public_user(conn, row)


def validate_card_payload(payload: CardPayload) -> None:
    order_no = payload.order_no.strip()
    item_type = payload.item_type.strip()
    if order_no and not ORDER_NO_PATTERN.fullmatch(order_no):
        raise HTTPException(status_code=400, detail="受注番号は E-25086 のように 英字1文字-5桁 で入力してください")
    if item_type and not ITEM_TYPE_PATTERN.fullmatch(item_type):
        raise HTTPException(status_code=400, detail="種別は2桁の数字で入力してください")
    if payload.completed_qty > payload.total_qty:
        raise HTTPException(status_code=400, detail="完了数は総数を超えられません")
    if payload.status not in {"未着手", "作業中", "完了"}:
        raise HTTPException(status_code=400, detail="不正なステータスです")
    validate_iso_date(payload.planned_work_date, "予定作業日")
    validate_iso_date(payload.due_date, "納期")


def escape_csv_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def hydrate_card(conn: sqlite3.Connection, card_row: sqlite3.Row) -> dict[str, Any]:
    card = dict(card_row)
    card["progress_rate"] = round((card["completed_qty"] / card["total_qty"]) * 100) if card["total_qty"] else 0
    card["assignee"] = row_to_dict(
        conn.execute("SELECT * FROM assignees WHERE id = ?", (card["assignee_id"],)).fetchone()
    )
    card["process"] = row_to_dict(
        conn.execute("SELECT * FROM processes WHERE id = ?", (card["current_process_id"],)).fetchone()
    )
    card["tags"] = [
        dict(row)
        for row in conn.execute(
            """
            SELECT t.* FROM tags t
            JOIN card_tags ct ON ct.tag_id = t.id
            WHERE ct.card_id = ?
            ORDER BY t.id
            """,
            (card["id"],),
        ).fetchall()
    ]
    return card


def get_card_or_404(conn: sqlite3.Connection, card_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="カードが見つかりません")
    return hydrate_card(conn, row)


def get_card_detail_or_404(conn: sqlite3.Connection, card_id: int) -> dict[str, Any]:
    card = get_card_or_404(conn, card_id)
    card["comments"] = [
        dict(row)
        for row in conn.execute(
            """
            SELECT comments.*, assignees.name AS user_name
            FROM comments
            LEFT JOIN assignees ON assignees.id = comments.user_id
            WHERE comments.card_id = ?
            ORDER BY comments.created_at DESC, comments.id DESC
            """,
            (card_id,),
        ).fetchall()
    ]
    card["work_logs"] = [
        dict(row)
        for row in conn.execute(
            """
            SELECT wl.*, a.name AS assignee_name, c.comment_type, c.body AS comment_body
            FROM work_logs wl
            LEFT JOIN assignees a ON a.id = wl.assignee_id
            LEFT JOIN comments c ON c.id = wl.comment_id
            WHERE wl.card_id = ?
            ORDER BY wl.created_at DESC, wl.id DESC
            """,
            (card_id,),
        ).fetchall()
    ]
    return card


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    with db() as conn:
        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND password_hash = ? AND active = 1
            """,
            (payload.username.strip(), hash_password(payload.password)),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="ユーザー名またはパスワードが違います")
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions(token, user_id, created_at) VALUES (?, ?, ?)", (token, user["id"], now_iso()))
        return {"token": token, "user": public_user(conn, user)}


@app.get("/api/auth/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return user


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None), user: dict[str, Any] = Depends(current_user)) -> dict[str, str]:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    return {"status": "ok"}


@app.get("/api/meta")
def meta(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with db() as conn:
        return {
            "processes": [dict(row) for row in conn.execute("SELECT * FROM processes ORDER BY sort_order")],
            "assignees": [dict(row) for row in conn.execute("SELECT * FROM assignees WHERE active = 1 ORDER BY id")],
            "tags": [dict(row) for row in conn.execute("SELECT * FROM tags ORDER BY id")],
            "comment_types": sorted(COMMENT_TYPES),
        }


@app.get("/api/cards")
def list_cards(
    process_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    tag: Optional[str] = None,
    user: dict[str, Any] = Depends(current_user),
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


@app.post("/api/cards")
def create_card(payload: CardPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    validate_card_payload(payload)
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO cards(
                order_no, item_type, drawing_no, item_name, remarks,
                total_qty, completed_qty, current_process_id, status,
                assignee_id, planned_work_date, due_date, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.order_no.strip(),
                payload.item_type.strip(),
                payload.drawing_no,
                payload.item_name,
                payload.remarks.strip(),
                payload.total_qty,
                payload.completed_qty,
                payload.current_process_id,
                payload.status,
                payload.assignee_id,
                payload.planned_work_date,
                payload.due_date,
                payload.description,
                now_iso(),
                now_iso(),
            ),
        )
        card_id = cur.lastrowid
        for tag_id in payload.tag_ids:
            conn.execute("INSERT OR IGNORE INTO card_tags(card_id, tag_id) VALUES (?, ?)", (card_id, tag_id))
        return get_card_or_404(conn, card_id)


@app.get("/api/cards/{card_id}")
def card_detail(card_id: int, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with db() as conn:
        return get_card_detail_or_404(conn, card_id)


@app.put("/api/cards/{card_id}")
def update_card(card_id: int, payload: CardPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    validate_card_payload(payload)
    with db() as conn:
        get_card_or_404(conn, card_id)
        conn.execute(
            """
            UPDATE cards SET
                order_no = ?, item_type = ?, drawing_no = ?, item_name = ?, remarks = ?,
                total_qty = ?, completed_qty = ?,
                current_process_id = ?, status = ?, assignee_id = ?, planned_work_date = ?,
                due_date = ?, description = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.order_no.strip(),
                payload.item_type.strip(),
                payload.drawing_no,
                payload.item_name,
                payload.remarks.strip(),
                payload.total_qty,
                payload.completed_qty,
                payload.current_process_id,
                payload.status,
                payload.assignee_id,
                payload.planned_work_date,
                payload.due_date,
                payload.description,
                now_iso(),
                card_id,
            ),
        )
        conn.execute("DELETE FROM card_tags WHERE card_id = ?", (card_id,))
        for tag_id in payload.tag_ids:
            conn.execute("INSERT OR IGNORE INTO card_tags(card_id, tag_id) VALUES (?, ?)", (card_id, tag_id))
        return get_card_or_404(conn, card_id)


@app.post("/api/cards/{card_id}/comments")
def add_comment(card_id: int, payload: CommentPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正なコメント種別です")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="コメントを入力してください")
    with db() as conn:
        get_card_or_404(conn, card_id)
        user_id = user["assignee_id"] or payload.user_id
        cur = conn.execute(
            "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (card_id, payload.comment_type, payload.body.strip(), user_id, now_iso()),
        )
        return dict(conn.execute("SELECT * FROM comments WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.post("/api/cards/{card_id}/work-results")
def register_work_result(card_id: int, payload: WorkResultPayload, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if payload.comment_type not in COMMENT_TYPES:
        raise HTTPException(status_code=400, detail="不正なコメント種別です")
    work_date = validate_iso_date(payload.work_date, "作業日") or date.today().isoformat()
    if payload.completed_qty_delta == 0 and payload.work_hours == 0 and not payload.comment.strip():
        raise HTTPException(status_code=400, detail="作業実績を入力してください")
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        card = get_card_or_404(conn, card_id)
        new_completed = card["completed_qty"] + payload.completed_qty_delta
        if new_completed > card["total_qty"]:
            raise HTTPException(status_code=400, detail="今回完了数を加えると総数を超えます")
        comment_id = None
        worker_id = payload.assignee_id or user["assignee_id"] or card["assignee_id"]
        if payload.comment.strip():
            cur = conn.execute(
                "INSERT INTO comments(card_id, comment_type, body, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (card_id, payload.comment_type, payload.comment.strip(), worker_id, now_iso()),
            )
            comment_id = cur.lastrowid
        status = "完了" if new_completed >= card["total_qty"] else ("作業中" if new_completed > 0 else card["status"])
        conn.execute(
            "UPDATE cards SET completed_qty = ?, status = ?, updated_at = ? WHERE id = ?",
            (new_completed, status, now_iso(), card_id),
        )
        conn.execute(
            """
            INSERT INTO work_logs(card_id, assignee_id, process_id, work_date, completed_qty_delta, work_hours, comment_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                worker_id,
                card["current_process_id"],
                work_date,
                payload.completed_qty_delta,
                payload.work_hours,
                comment_id,
                now_iso(),
            ),
        )
        return get_card_detail_or_404(conn, card_id)


@app.get("/api/reports/daily")
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


@app.get("/api/reports/daily.csv")
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, app_dir=str(Path(__file__).parent))

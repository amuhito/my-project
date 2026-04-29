from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from auth import hash_password
from constants import DEFAULT_PASSWORD, DESCRIPTION_TEMPLATE, PROCESSES
from database import db, ensure_column, table_has_rows
from utils import now_iso


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
        "SH-208500L2": ("E-25086", "01", "内面研磨優先"),
        "HB-110470": ("S-26654", "02", ""),
        "RW-001": ("P-66538", "03", "外注戻り後の追加工"),
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


def allow_negative_work_log_delta(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'work_logs'").fetchone()
    if not row or "completed_qty_delta >= 0" not in row["sql"]:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE work_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            assignee_id INTEGER REFERENCES assignees(id),
            registered_by_user_id INTEGER REFERENCES users(id),
            process_id INTEGER REFERENCES processes(id),
            work_type TEXT NOT NULL DEFAULT '作業',
            work_date TEXT NOT NULL,
            completed_qty_delta INTEGER NOT NULL,
            work_hours REAL NOT NULL CHECK(work_hours >= 0),
            comment_id INTEGER REFERENCES comments(id),
            created_at TEXT NOT NULL
        );
        INSERT INTO work_logs_new(
            id, card_id, assignee_id, registered_by_user_id, process_id, work_type, work_date,
            completed_qty_delta, work_hours, comment_id, created_at
        )
        SELECT
            id, card_id, assignee_id, registered_by_user_id, process_id, '作業', work_date,
            completed_qty_delta, work_hours, comment_id, created_at
        FROM work_logs;
        DROP TABLE work_logs;
        ALTER TABLE work_logs_new RENAME TO work_logs;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


def sync_comment_classification_constraint(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'comments'").fetchone()
    if not row or "気づき" not in row["sql"]:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE comments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            comment_type TEXT NOT NULL CHECK(comment_type IN ('開始', '作業', '手戻り', 'コメント')),
            body TEXT NOT NULL,
            user_id INTEGER REFERENCES assignees(id),
            created_at TEXT NOT NULL
        );
        INSERT INTO comments_new(id, card_id, comment_type, body, user_id, created_at)
        SELECT
            id,
            card_id,
            CASE WHEN comment_type IN ('開始', '作業', '手戻り', 'コメント') THEN comment_type ELSE 'コメント' END,
            body,
            user_id,
            created_at
        FROM comments;
        DROP TABLE comments;
        ALTER TABLE comments_new RENAME TO comments;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


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
                comment_type TEXT NOT NULL CHECK(comment_type IN ('開始', '作業', '手戻り', 'コメント')),
                body TEXT NOT NULL,
                user_id INTEGER REFERENCES assignees(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                assignee_id INTEGER REFERENCES assignees(id),
                registered_by_user_id INTEGER REFERENCES users(id),
                process_id INTEGER REFERENCES processes(id),
                work_type TEXT NOT NULL DEFAULT '作業',
                work_date TEXT NOT NULL,
                completed_qty_delta INTEGER NOT NULL,
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
                password_must_change INTEGER NOT NULL DEFAULT 1,
                password_changed_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS card_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id),
                action TEXT NOT NULL,
                before_json TEXT,
                after_json TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        ensure_column(conn, "cards", "order_no", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "cards", "item_type", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "cards", "remarks", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "work_logs", "process_id", "INTEGER REFERENCES processes(id)")
        ensure_column(conn, "work_logs", "registered_by_user_id", "INTEGER REFERENCES users(id)")
        ensure_column(conn, "work_logs", "work_type", "TEXT NOT NULL DEFAULT '作業'")
        allow_negative_work_log_delta(conn)
        sync_comment_classification_constraint(conn)
        conn.execute(
            """
            UPDATE work_logs
            SET work_type = COALESCE(
                (
                    SELECT CASE
                        WHEN comments.comment_type IN ('開始', '作業', '手戻り', 'コメント') THEN comments.comment_type
                        ELSE 'コメント'
                    END
                    FROM comments
                    WHERE comments.id = work_logs.comment_id
                ),
                work_type,
                '作業'
            )
            """
        )
        ensure_column(conn, "users", "password_must_change", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(conn, "users", "password_changed_at", "TEXT")
        ensure_column(conn, "sessions", "expires_at", "TEXT")
        conn.execute("UPDATE sessions SET expires_at = ? WHERE expires_at IS NULL OR expires_at = ''", (now_iso(),))
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
                ("E-25086", "01", "SH-208500L2", "シュート", "内面研磨優先", 61, 15, "内面研磨", "作業中", "三谷", today, today + timedelta(days=5), ["至急"]),
                ("S-26654", "02", "HB-110470", "平刃", "", 8, 0, "刃物研磨", "未着手", "山本", today + timedelta(days=1), today + timedelta(days=7), ["厳守"]),
                ("P-66538", "03", "RW-001", "外注戻り追加工品", "外注戻り後の追加工", 3, 0, "機械加工", "未着手", "佐藤", today + timedelta(days=2), today + timedelta(days=4), ["追加工", "外注戻り"]),
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
                ("admin", "管理者", hash_password("admin123"), None, "admin", 1, 1, None, now_iso()),
                ("mitani", "三谷", hash_password(DEFAULT_PASSWORD), assignees.get("三谷"), "operator", 1, 1, None, now_iso()),
                ("yamamoto", "山本", hash_password(DEFAULT_PASSWORD), assignees.get("山本"), "operator", 1, 1, None, now_iso()),
                ("sato", "佐藤", hash_password(DEFAULT_PASSWORD), assignees.get("佐藤"), "operator", 1, 1, None, now_iso()),
                ("tanaka", "田中", hash_password(DEFAULT_PASSWORD), assignees.get("田中"), "operator", 1, 1, None, now_iso()),
                ("suzuki", "鈴木", hash_password(DEFAULT_PASSWORD), assignees.get("鈴木"), "operator", 1, 1, None, now_iso()),
            ]
            conn.executemany(
                """
                INSERT INTO users(username, display_name, password_hash, assignee_id, role, active, password_must_change, password_changed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                users,
            )

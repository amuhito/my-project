from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def get_db_path() -> Path:
    configured = os.getenv("KANBAN_DB_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return BASE_DIR / "kanban.db"


DB_PATH = get_db_path()

DEFAULT_BOARD_TITLE = "納期確認ボード"
DEFAULT_LIST_TITLES = [
    "未対応",
    "設計確認中",
    "発注中",
    "サプライヤー確認中",
    "１次対応完了",
]


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS board (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS board_list (
                id INTEGER PRIMARY KEY,
                board_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (board_id) REFERENCES board(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS card (
                id INTEGER PRIMARY KEY,
                list_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                labels_json TEXT NOT NULL DEFAULT '[]',
                due_date TEXT,
                project_no TEXT NOT NULL DEFAULT '',
                customer_name TEXT NOT NULL DEFAULT '',
                received_date TEXT,
                requested_due_date TEXT,
                assignee_name TEXT NOT NULL DEFAULT '',
                response_due_date TEXT,
                earliest_ship_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                history_text TEXT NOT NULL DEFAULT '',
                archived INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL,
                FOREIGN KEY (list_id) REFERENCES board_list(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS comment (
                id INTEGER PRIMARY KEY,
                card_id INTEGER NOT NULL,
                author_user_id INTEGER,
                author TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (card_id) REFERENCES card(id) ON DELETE CASCADE,
                FOREIGN KEY (author_user_id) REFERENCES user_account(id)
            );

            CREATE TABLE IF NOT EXISTS checklist_item (
                id INTEGER PRIMARY KEY,
                card_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL,
                FOREIGN KEY (card_id) REFERENCES card(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY,
                card_id INTEGER NOT NULL,
                actor_user_id INTEGER,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (card_id) REFERENCES card(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES user_account(id)
            );

            CREATE TABLE IF NOT EXISTS user_account (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_session (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user_account(id) ON DELETE CASCADE
            );
            """
        )
        migrate_card_table(connection)
        migrate_audit_tables(connection)

        board_count = connection.execute("SELECT COUNT(*) FROM board").fetchone()[0]
        if board_count == 0:
            seed_database(connection)
        else:
            ensure_default_lists(connection)


def ensure_default_lists(connection: sqlite3.Connection) -> None:
    board_row = connection.execute("SELECT id FROM board ORDER BY id ASC LIMIT 1").fetchone()
    if board_row is None:
        connection.execute("INSERT INTO board (id, title) VALUES (?, ?)", (1, DEFAULT_BOARD_TITLE))
        board_id = 1
    else:
        board_id = board_row["id"]
        connection.execute(
            "UPDATE board SET title = ? WHERE id = ?",
            (DEFAULT_BOARD_TITLE, board_id),
        )

    existing_lists = connection.execute(
        "SELECT id, position FROM board_list WHERE board_id = ? ORDER BY position ASC, id ASC",
        (board_id,),
    ).fetchall()

    for position, title in enumerate(DEFAULT_LIST_TITLES):
        if position < len(existing_lists):
            connection.execute(
                "UPDATE board_list SET title = ?, position = ? WHERE id = ?",
                (title, position, existing_lists[position]["id"]),
            )
        else:
            connection.execute(
                "INSERT INTO board_list (board_id, title, position) VALUES (?, ?, ?)",
                (board_id, title, position),
            )


def migrate_card_table(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(card)").fetchall()
    }
    required_columns = {
        "project_no": "TEXT NOT NULL DEFAULT ''",
        "customer_name": "TEXT NOT NULL DEFAULT ''",
        "received_date": "TEXT",
        "requested_due_date": "TEXT",
        "assignee_name": "TEXT NOT NULL DEFAULT ''",
        "response_due_date": "TEXT",
        "earliest_ship_date": "TEXT",
        "notes": "TEXT NOT NULL DEFAULT ''",
        "history_text": "TEXT NOT NULL DEFAULT ''",
        "archived": "INTEGER NOT NULL DEFAULT 0",
        "created_by_user_id": "INTEGER",
        "updated_by_user_id": "INTEGER",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in columns:
            connection.execute(f"ALTER TABLE card ADD COLUMN {column_name} {column_type}")


def migrate_audit_tables(connection: sqlite3.Connection) -> None:
    comment_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(comment)").fetchall()
    }
    if "author_user_id" not in comment_columns:
        connection.execute("ALTER TABLE comment ADD COLUMN author_user_id INTEGER")

    activity_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(activity)").fetchall()
    }
    if "actor_user_id" not in activity_columns:
        connection.execute("ALTER TABLE activity ADD COLUMN actor_user_id INTEGER")


def seed_database(connection: sqlite3.Connection) -> None:
    connection.execute("INSERT INTO board (id, title) VALUES (?, ?)", (1, DEFAULT_BOARD_TITLE))

    lists = [(index + 1, 1, title, index) for index, title in enumerate(DEFAULT_LIST_TITLES)]
    connection.executemany(
        "INSERT INTO board_list (id, board_id, title, position) VALUES (?, ?, ?, ?)",
        lists,
    )

    cards = [
        (
            1,
            1,
            "P-60855 味の素食品",
            "発送日の確認が必要です。現状はGW前納品が難しく、4月下旬回答予定です。",
            json.dumps(["発送日確認"], ensure_ascii=False),
            None,
            "P-60855",
            "味の素食品",
            "2026-03-02",
            "最短納期",
            "西",
            "2026-04-22",
            "2026-04-27",
            "現状、GW前の納品は難しく、納期回答は4月下旬予定です。",
            "3/17 中西へ状況共有済み",
            0,
        ),
        (
            2,
            2,
            "P-61046 ハウス食品",
            "営業部から要納期連絡あり。設計部へ確認中です。",
            json.dumps(["要確認"], ensure_ascii=False),
            None,
            "P-61046",
            "ハウス食品",
            "2026-03-12",
            None,
            "三恵",
            "2026-04-20",
            None,
            "営業部西村さんから要納期連絡。",
            "設計部へ確認依頼済み",
            0,
        ),
        (
            3,
            3,
            "P-61129 モスフード",
            "出荷は1か月後見込み。4月17日前後で一次回答予定です。",
            json.dumps(["納期短縮依頼"], ensure_ascii=False),
            None,
            "P-61129",
            "モスフード",
            "2026-03-25",
            None,
            "ハシャ",
            "2026-04-17",
            None,
            "出荷は1か月後見込みです。",
            "4/17 発送予定として一次回答予定",
            0,
        ),
        (
            4,
            4,
            "P-61312 東海化学",
            "部品を一から制作中のため、サプライヤーに追加確認を依頼しています。",
            json.dumps(["外注先"], ensure_ascii=False),
            None,
            "P-61312",
            "東海化学",
            "2026-04-06",
            None,
            "マサル",
            "2026-05-08",
            "2026-04-15",
            "部品を1から制作するため、約1か月の納期見込みです。",
            "4/6 木下へ状況共有済み",
            0,
        ),
        (
            5,
            5,
            "P-61141 霜玉米粒麦",
            "サーボモーター取消のため一次対応は完了。必要なら再確認します。",
            json.dumps(["完了"], ensure_ascii=False),
            None,
            "P-61141",
            "霜玉米粒麦",
            "2026-04-07",
            "最短納期",
            "安川",
            "2026-04-20",
            None,
            "サーボモーター取消のため一次対応完了です。",
            "必要時のみ再確認",
            0,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO card (
            id,
            list_id,
            title,
            description,
            labels_json,
            due_date,
            project_no,
            customer_name,
            received_date,
            requested_due_date,
            assignee_name,
            response_due_date,
            earliest_ship_date,
            notes,
            history_text,
            position
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        cards,
    )

    comments = [
        (1, 1, "西", "4月下旬回答予定で案内済みです。", "2026-04-06 10:00"),
        (2, 2, "川村", "営業部から急ぎ確認依頼が来ています。", "2026-04-06 14:30"),
    ]
    connection.executemany(
        "INSERT INTO comment (id, card_id, author, body, created_at) VALUES (?, ?, ?, ?, ?)",
        comments,
    )

    checklist_items = [
        (1, 1, "発送日の現状確認", 1, 0),
        (2, 1, "回答予定日を共有", 0, 1),
        (3, 2, "設計部へ確認依頼", 1, 0),
        (4, 2, "顧客向け回答文の準備", 0, 1),
    ]
    connection.executemany(
        """
        INSERT INTO checklist_item (id, card_id, text, completed, position)
        VALUES (?, ?, ?, ?, ?)
        """,
        checklist_items,
    )

    activities = [
        (1, 1, "カードを作成しました", "2026-04-05 09:00"),
        (2, 1, "チェックリストを追加しました", "2026-04-06 09:30"),
        (3, 2, "期限を設定しました", "2026-04-06 13:00"),
        (4, 4, "サプライヤー確認中に移動しました", "2026-04-06 18:20"),
    ]
    connection.executemany(
        "INSERT INTO activity (id, card_id, message, created_at) VALUES (?, ?, ?, ?)",
        activities,
    )

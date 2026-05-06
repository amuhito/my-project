# 機械課 工程見える化PoC

Trello風ボードとカレンダーで、加工・研磨・追加工の進捗を軽く入力できるPoCです。

## 構成

- Frontend: React / TypeScript / Vite
- Backend: FastAPI
- DB: SQLite

## 主な機能

- ログインとBearer tokenセッション
- 工程別ボード
- 島別、担当者別、カレンダー表示
- カード詳細、作業実績、作業ログ
- 日報検索とCSV出力
- 管理画面でのユーザー、担当者、タグ管理
- 起動時のPoCデータ正規化

## 起動

backend:

```bash
make setup-backend
make dev-backend
```

frontend:

```bash
make setup-frontend
make dev-frontend
```

起動後のURL:

- Frontend: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/api/health`

DBは `backend/machine_poc.sqlite3` に自動作成されます。

## ログイン

初期ユーザーはDB初期化時に作成されます。初回ログイン後にパスワード変更が必要です。

管理者:

- username: `admin`
- password: `admin123`

作業者:

| username | 表示名 | 初期パスワード |
| --- | --- | --- |
| `mitani` | 三谷 | `password` |
| `yamamoto` | 山本 | `password` |
| `sato` | 佐藤 | `password` |
| `tanaka` | 田中 | `password` |
| `suzuki` | 鈴木 | `password` |

## 検証

```bash
make check
```

共通の開発手順はリポジトリルートの `docs/development.md` にもまとめています。

PR検証で別の仮想環境を使う場合:

```bash
'/path/to/.venv/bin/python' -m pytest backend/tests
'/path/to/.venv/bin/python' -m compileall backend
npm run build
```

## 生成物

以下はGit管理対象外です。

- `.venv/`
- `node_modules/`
- `dist/`
- `backend/*.sqlite3`
- `__pycache__/`
- `.pytest_cache/`

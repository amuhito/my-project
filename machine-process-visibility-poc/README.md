# 機械課 工程見える化PoC

Trello風ボードとカレンダーで、加工・研磨・追加工の進捗を軽く入力できるPoCです。

## 構成

- Frontend: React / TypeScript / Vite
- Backend: FastAPI
- DB: SQLite

## 起動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/main.py
```

別ターミナル:

```bash
npm install
npm run dev
```

フロントエンド: http://localhost:5173
API: http://localhost:8000

DBは `backend/machine_poc.sqlite3` に自動作成されます。

## 初期ログイン

- 管理者: `admin` / `admin123`
- 三谷: `mitani` / `password`
- 山本: `yamamoto` / `password`
- 佐藤: `sato` / `password`
- 田中: `tanaka` / `password`
- 鈴木: `suzuki` / `password`

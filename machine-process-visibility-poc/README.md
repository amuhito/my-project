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

## ログイン

初期ユーザーは DB 初期化時に作成されます。初回ログイン後にパスワード変更が必要です。
初期パスワードは管理者から利用者へ個別に共有してください。

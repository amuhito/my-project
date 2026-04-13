# Delivery Kanban Cloud

このフォルダは、納期確認カンバン POC のクラウド向け構成です。

## できること

- FastAPI が `/api` を提供
- React をビルドして同じアプリから配信
- SQLite の保存先を環境変数で切替
- CORS 設定を環境変数で切替
- Docker 1 本でクラウドへ載せやすい構成

## プロジェクト構成（主要ディレクトリ）

```text
delivery-kanban-poc/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI エントリポイント
│   │   ├── database.py        # SQLite 初期化・接続
│   │   └── ...
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # React エントリポイント
│   │   ├── api.ts             # API 呼び出し層
│   │   └── ...
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
└── README.md
```

## ローカル開発（Mac 優先）

前提:

- `python3`（推奨: 3.12 系）
- `node` / `npm`（推奨: Node 22 系）

### 1. backend 起動（ターミナル1）

```bash
cd /path/to/delivery-kanban-poc/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. frontend 起動（ターミナル2）

```bash
cd /path/to/delivery-kanban-poc/frontend
cp .env.example .env
npm install
npm run dev
```

起動後のURL（開発時）:

- frontend: `http://127.0.0.1:5173`
- backend API: `http://127.0.0.1:8000`

補足:

- `frontend/src/api.ts` は開発時に `http://127.0.0.1:8000` を既定値として使います。
- `.env` を使う場合は `VITE_API_BASE_URL` で明示的にAPI先を上書きできます。

### 3. ログイン

起動後はログイン画面が表示されます。初期ユーザーは次の値です。

- username: `admin`
- password: `admin1234`

`admin` でログインすると、画面右上に「ユーザー管理」ボタンが表示されます。
この画面でユーザー一覧の確認と新規ユーザー追加ができます。

APIで追加する場合は、ログイン後に `POST /api/auth/users` を使います。

```bash
curl -X POST "http://127.0.0.1:8000/api/auth/users" \
  -H "Authorization: Bearer <LOGIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"username":"sato","display_name":"佐藤","password":"SatoPass123"}'
```

## Docker 起動

```bash
cd /path/to/delivery-kanban-poc
docker compose up --build
```

起動後の URL:

- App: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/api/health`

## 環境変数

- `KANBAN_DB_PATH`
  SQLite ファイルの保存先
- `KANBAN_CORS_ORIGINS`
  許可オリジンのカンマ区切り。単一コンテナ運用なら `*` で開始可能
- `KANBAN_FRONTEND_DIST`
  配信用フロントエンド `dist` のパス
- `KANBAN_INITIAL_USERNAME`
  初回起動時に自動作成する初期ユーザー名（既定: `admin`）
- `KANBAN_INITIAL_DISPLAY_NAME`
  初回起動時に自動作成する初期表示名（既定: `管理者`）
- `KANBAN_INITIAL_PASSWORD`
  初回起動時に自動作成する初期パスワード（既定: `admin1234`）
- `KANBAN_SESSION_HOURS`
  ログインセッションの有効時間（時間、既定: `12`）
- `VITE_API_BASE_URL`
  開発時の API ベース URL。未設定時は同一オリジンの `/api` を使います

## AWS 展開

2026年4月10日時点では、AWS App Runner は公式資料内で新規利用終了日の表記に差分があります。

- 可用性変更の案内ページ: `2026年4月30日` から新規利用者向けにクローズ
- API リファレンスの一部: `2026年3月31日` と記載

そのため、この POC を今から新規に AWS へ載せる最小案としては Lightsail Container Service を推奨しています。

- Lightsail 手順: [docs/aws-lightsail-deploy.md](docs/aws-lightsail-deploy.md)
- App Runner 補足: [docs/aws-apprunner-note.md](docs/aws-apprunner-note.md)

## 補足

SQLite のままでも POC や少人数検証には使えますが、継続運用や同時更新が増える場合は PostgreSQL などへの移行をおすすめします。

## 今後のタスク（タイムゾーン）

- 対応済み（暫定）: コンテナの `TZ` を `Asia/Tokyo` に設定
- 今後実施（推奨）:
  - バックエンド保存時刻を UTC（ISO 8601）で統一
  - フロント表示時にユーザーのローカル時刻へ変換
  - 既存データの時刻フォーマット移行方針を定義

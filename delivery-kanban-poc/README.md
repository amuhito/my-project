# Delivery Kanban Cloud

このフォルダは、納期確認カンバン POC のクラウド向け構成です。

## できること

- FastAPI が `/api` を提供
- React をビルドして同じアプリから配信
- SQLite の保存先を環境変数で切替
- CORS 設定を環境変数で切替
- Docker 1 本でクラウドへ載せやすい構成
- フェーズ1-A: 「親=問い合わせ / 子=案件（P/E/S）」の二層管理

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
- 社内本番移行チェックリスト: [docs/production-migration-checklist.md](docs/production-migration-checklist.md)

## 補足

SQLite のままでも POC や少人数検証には使えますが、継続運用や同時更新が増える場合は PostgreSQL などへの移行をおすすめします。

## 画面構成（正式導線）

正式運用の導線は以下です。旧カード構造画面は通常導線から到達しません。

1. 問い合わせ一覧
2. 新規問い合わせ作成
3. 問い合わせ詳細（親情報・子案件一覧・親コメント）
4. 子案件カンバン
5. 子案件編集モーダル

## 問い合わせ作成

1. `新規問い合わせ` で `納入先` と `受注No` を入力
2. `希望納期種別` を選択
  - `最短`（`requested_due_type=shortest`）
  - `指定日`（`requested_due_type=specific`）
3. `依頼内容` を選択
  - `納期確認依頼`
  - `納期短縮依頼`
4. 送信時に問い合わせ（親）と子案件（P/E/S）を生成

受注Noは改行 / `,` / `、` 区切りに対応し、範囲記法 `P-61057～63` も展開します。

## コメント運用（親問い合わせ）

- 問い合わせ詳細の下部で親問い合わせコメントを管理
- コメント種別:
  - `通常コメント`
  - `差し戻し`
- 本フェーズでは通知・メンション・既読管理は未実装

## 子案件更新方法

- 子案件カンバンカードから編集を開き、以下を更新
  - 工程（未出図 / 調達中 / 検査・表面処理 / 組付け / 梱包 / 発送完了）
  - 担当
  - 状態（通常 / 待ち / 完了）
  - 最終入荷予定日
  - 最終渡し日
  - 組付け完了日
  - 梱包完了日
  - 発送予定日
  - 備考
- 保存後は一覧・カンバンに即時反映

## 出図済み判定

- 子案件編集の `出図済みにして手配開始` を押すと以下を更新
  - `drawing_ready_confirmed = true`
  - `drawing_ready_confirmed_at = 実行時刻`
  - `process = 調達中`

## 希望納期と発送予定日

- 希望納期:
  - 問い合わせ（親）が持つ営業依頼納期
  - `最短` または `指定日`
- 発送予定日:
  - 子案件（案件）ごとの現場・購買の予定値
  - 手入力で更新

## 正式な日付項目名（R4）

現在の公開APIおよびフロントで正式に扱う日付項目は以下です。

- `final_arrival_planned_date`（最終入荷予定日）
- `final_handover_date`（最終渡し日）
- `assembly_completed_date`（組付け完了日）
- `packing_completed_date`（梱包完了日）
- `shipping_planned_date`（発送予定日）

補足:
- 旧名（`planned_arrival_date` / `actual_arrival_date` / `packing_due_date` / `confirmed_shipping_date`）は R4 で廃止済みです。
- API とフロントは新ドメイン名のみを扱います。

## R4 migration 手順（ローカル/AWS 共通）

1. DBバックアップを取得
   - SQLite 既定パス: `backend/kanban.db`
   - 例: `cp backend/kanban.db backend/kanban.db.bak-$(date +%Y%m%d-%H%M%S)`
2. アプリを起動（起動時に migration 実行）
   - backend: `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
3. 起動ログにエラーがないことを確認
4. 問い合わせ一覧 / 詳細 / 子案件編集 / カンバン移動を確認

補足:
- R4 migration は `inquiry_item` テーブルの旧日付列を新日付列へデータコピーし、旧列を含まない新テーブルへ再構築します。
- 既存データ保全のため、migration 前バックアップは必須です。

## 旧構造の扱い（非推奨）

- `card` テーブルと `/api/board`, `/api/cards*`, `/api/lists/*/cards` は後方互換のため残置
- 旧構造は正式運用対象外
- 新規機能は問い合わせ（親）/子案件（子）の新構造のみを対象に実装

## 既存データ移行（1-A）

- 起動時に `inquiry` / `inquiry_item` テーブルを自動作成
- 既存 `card` データは初回起動時に仮問い合わせへコピー移行
- 旧 `card` は残し、`inquiry_item.legacy_card_id` で移行済み管理
- `requested_due_date` が日付形式でない場合は `requested_due_type=shortest` として移行

## 今後のタスク（タイムゾーン）

- 対応済み（暫定）: コンテナの `TZ` を `Asia/Tokyo` に設定
- 対応済み（推奨）:
  - バックエンド保存時刻を UTC（ISO 8601）で統一
  - フロント表示時にユーザーのローカル時刻へ変換
- 今後実施:
  - 既存データ（旧フォーマット時刻）の移行方針を定義

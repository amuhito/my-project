# Delivery Kanban Cloud

このフォルダは、納期確認カンバン POC のクラウド向け構成です。

## できること

- FastAPI が `/api` を提供
- React をビルドして同じアプリから配信
- SQLite の保存先を環境変数で切替
- CORS 設定を環境変数で切替
- Docker 1 本でクラウドへ載せやすい構成

## ローカル開発

### バックエンド

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### フロントエンド

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc\frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

開発時の URL:

- Frontend: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`

## Docker 起動

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc
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
- `VITE_API_BASE_URL`
  開発時の API ベース URL。未設定時は同一オリジンの `/api` を使います

## AWS 展開

2026年4月10日時点では、AWS App Runner は公式資料内で新規利用終了日の表記に差分があります。

- 可用性変更の案内ページ: `2026年4月30日` から新規利用者向けにクローズ
- API リファレンスの一部: `2026年3月31日` と記載

そのため、この POC を今から新規に AWS へ載せる最小案としては Lightsail Container Service を推奨しています。

- Lightsail 手順: [aws-lightsail-deploy.md](C:\Users\A000594001\my-project\delivery-kanban-poc\docs\aws-lightsail-deploy.md)
- App Runner 補足: [aws-apprunner-note.md](C:\Users\A000594001\my-project\delivery-kanban-poc\docs\aws-apprunner-note.md)

## 補足

SQLite のままでも POC や少人数検証には使えますが、継続運用や同時更新が増える場合は PostgreSQL などへの移行をおすすめします。

# Delivery Kanban Local

このフォルダは、`delivery-kanban-poc` をローカル PC 上で起動するためのローカル向けパッケージです。
`machine-process-visibility-poc` など、他のPoCの起動には使いません。

アプリ本体は次のフォルダを使います。

- [backend](C:\Users\A000594001\my-project\delivery-kanban-poc\backend)
- [frontend](C:\Users\A000594001\my-project\delivery-kanban-poc\frontend)

## 使い方

### まとめて起動

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc-local
powershell -ExecutionPolicy Bypass -File .\start-local.ps1
```

または:

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc-local
.\start-local.cmd
```

これでバックエンド用とフロントエンド用の PowerShell が別ウィンドウで開きます。

### 個別起動

バックエンドだけ起動する場合:

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc-local
.\start-backend.cmd
```

フロントエンドだけ起動する場合:

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc-local
.\start-frontend.cmd
```

## アクセス先

- Frontend: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`

## 補足

- 初回起動時は必要に応じて `python -m venv .venv`、`pip install -r requirements.txt`、`npm.cmd install` を自動実行します
- PowerShell の実行ポリシー対策として、`-ExecutionPolicy Bypass` 前提で起動する構成です
- ローカル版はクラウド版と同じアプリ本体を使うため、機能差分はありません
- スクリプト内では、親ディレクトリ配下の `delivery-kanban-poc/backend` と `delivery-kanban-poc/frontend` を参照します

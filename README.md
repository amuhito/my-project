# Project Overview

このリポジトリには、納期確認向けのカンバン POC と既存スクリプト群が入っています。

## ディレクトリ構成

- `delivery-kanban-poc`
  React + TypeScript + Vite のフロントエンドと、FastAPI + SQLite のバックエンドを含むアプリ本体
- `delivery-kanban-poc-local`
  ローカル PC で起動しやすくするための起動スクリプト群
- `tools/misumi_types`
  既存の Python / PowerShell スクリプト群

## 納期確認カンバン POC

アプリ本体は `delivery-kanban-poc` 配下にあります。

- フロントエンド: `delivery-kanban-poc/frontend`
- バックエンド: `delivery-kanban-poc/backend`
- クラウド向け README: `delivery-kanban-poc/README.md`

ローカル利用の入口は `delivery-kanban-poc-local` にあります。

- まとめて起動: `delivery-kanban-poc-local/start-local.cmd`
- バックエンドのみ: `delivery-kanban-poc-local/start-backend.cmd`
- フロントエンドのみ: `delivery-kanban-poc-local/start-frontend.cmd`
- ローカル向け README: `delivery-kanban-poc-local/README.md`

## ローカル起動

最短なら次を実行してください。

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc-local
.\start-local.cmd
```

起動後の URL:

- Frontend: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`

## 既存スクリプト

既存スクリプトの説明は [tools/misumi_types/README.md](C:\Users\A000594001\my-project\tools\misumi_types\README.md) を参照してください。

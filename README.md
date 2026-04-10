# Project Overview

このリポジトリには、納期確認向けのカンバン POC と既存スクリプト群が入っています。

## ディレクトリ構成

- `delivery-kanban-poc`
  React + TypeScript + Vite のフロントエンドと、FastAPI + SQLite のバックエンドをまとめたアプリ本体
- `tools/misumi_types`
  既存の Python / PowerShell スクリプト群

## 納期確認カンバン POC

アプリ本体は `delivery-kanban-poc` 配下にあります。

- フロントエンド: `delivery-kanban-poc/frontend`
- バックエンド: `delivery-kanban-poc/backend`

### 起動手順

1. バックエンド

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

依存が未導入なら最初に一度だけ:

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. フロントエンド

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc\frontend
npm.cmd run dev
```

依存が未導入なら最初に一度だけ:

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc\frontend
npm.cmd install
```

### アクセス先

- API: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

## 既存スクリプト

既存スクリプトの説明は [tools/misumi_types/README.md](C:\Users\A000594001\my-project\tools\misumi_types\README.md) にまとめています。

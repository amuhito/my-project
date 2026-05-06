# Development Guide

このリポジトリには複数のPoCと既存スクリプトがあります。作業するときは、対象ディレクトリを明確にしてから依存関係のインストールや起動を行ってください。

## 対象アプリ

| 対象 | ディレクトリ | backend | frontend |
| --- | --- | --- | --- |
| 納期確認カンバンPoC | `apps/delivery-kanban/` | `apps/delivery-kanban/backend/` | `apps/delivery-kanban/frontend/` |
| 機械課 工程見える化PoC | `apps/machine-process-visibility/` | `apps/machine-process-visibility/backend/` | `apps/machine-process-visibility/` |

`scripts/delivery-kanban-local/` は、`apps/delivery-kanban/` 専用のWindows向け起動補助です。機械課PoCの起動には使いません。

## 納期確認カンバンPoC

backend:

```bash
cd apps/delivery-kanban/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

frontend:

```bash
cd apps/delivery-kanban/frontend
cp .env.example .env
npm install
npm run dev
```

build:

```bash
cd apps/delivery-kanban/frontend
npm run build
```

## 機械課 工程見える化PoC

backend:

```bash
cd apps/machine-process-visibility
make setup-backend
make dev-backend
```

frontend:

```bash
cd apps/machine-process-visibility
make setup-frontend
make dev-frontend
```

validation:

```bash
cd apps/machine-process-visibility
make check
```

リポジトリルートから実行する場合は、次の委譲ターゲットも使えます。

```bash
make machine-install
make machine-check
```

## 生成物の扱い

以下はGit管理に含めないでください。

- Python仮想環境: `.venv/`
- Node依存: `node_modules/`
- frontend build: `dist/`
- SQLite DB: `*.sqlite3`, `backend/kanban.db`
- Python cache: `__pycache__/`, `.pytest_cache/`

## PR作成時の注意

- 機能追加とディレクトリ移動は分けてください。
- 別PoCのファイルを同じPRで触る場合は、PR本文に理由を書いてください。
- 変更対象のPoCで、少なくともbuildまたはテストを1つ実行してください。

## CI

機械課PoCは `.github/workflows/machine-process-visibility.yml` で検証します。

- backend dependencies: `make -C apps/machine-process-visibility setup-backend`
- frontend dependencies: `npm ci`
- validation: `make machine-check`

workflowは `apps/machine-process-visibility/`、root `Makefile`、関連開発ドキュメントが変わったときに実行されます。

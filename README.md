# my-project

このリポジトリは、業務改善向けのPoCアプリと既存スクリプトをまとめて管理しています。

## 入口

| ディレクトリ | 役割 | 主な利用者 |
| --- | --- | --- |
| `delivery-kanban-poc/` | 納期確認カンバンPoC本体。React frontend、FastAPI backend、Docker構成を含みます。 | 納期確認カンバンの開発・検証 |
| `delivery-kanban-poc-local/` | `delivery-kanban-poc/` をWindowsローカルPCで起動するための補助スクリプト群です。 | ローカル利用者 |
| `machine-process-visibility-poc/` | 機械課 工程見える化PoC。工程ボード、作業実績、日報、管理機能を含みます。 | 機械課PoCの開発・検証 |
| `tools/misumi_types/` | 既存のPython / PowerShellスクリプト群です。 | 既存スクリプト利用者 |

## 現在の構成方針

- `delivery-kanban-poc/` と `machine-process-visibility-poc/` は別アプリとして扱います。
- `delivery-kanban-poc-local/` はアプリ本体ではなく、`delivery-kanban-poc/` 専用の起動補助です。
- 新しいPoCやアプリを追加するときは、既存アプリの中へ混ぜず、独立したディレクトリとして追加します。
- ディレクトリ再編は機能追加PRと分けて、段階的に実施します。

将来の整理案は [docs/repo-organization.md](docs/repo-organization.md) を参照してください。

開発・検証コマンドの一覧は [docs/development.md](docs/development.md) を参照してください。

## 納期確認カンバンPoC

詳細は [delivery-kanban-poc/README.md](delivery-kanban-poc/README.md) を参照してください。

ローカルPCで簡単に起動する場合は、補助スクリプトを使います。

```powershell
cd C:\Users\A000594001\my-project\delivery-kanban-poc-local
.\start-local.cmd
```

起動後のURL:

- Frontend: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`

## 機械課 工程見える化PoC

詳細は [machine-process-visibility-poc/README.md](machine-process-visibility-poc/README.md) を参照してください。

```bash
cd machine-process-visibility-poc
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/main.py
```

別ターミナル:

```bash
cd machine-process-visibility-poc
npm install
npm run dev
```

起動後のURL:

- Frontend: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`

## 既存スクリプト

既存スクリプトの説明は `tools/misumi_types/README.md` を参照してください。

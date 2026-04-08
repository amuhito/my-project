# Project Overview

このリポジトリには、既存の `misumi_types` スクリプト群と、ローカル動作する納期確認向けカンバン POC が含まれています。用途ごとにディレクトリを分け、ルートには全体の案内だけを置く構成です。

## ディレクトリ構成

- `frontend`
  React + TypeScript + Vite のフロントエンド
- `backend`
  FastAPI + SQLite のバックエンド
- `tools/misumi_types`
  既存の Python / PowerShell スクリプト、設定、ログ、退避ファイル

## 納期確認カンバン POC

主な機能:

- 日本語 UI のカンバン表示
- グループ: `未対応` / `設計確認中` / `発注中` / `サプライヤー確認中` / `１次対応完了`
- 案件専用フィールド
  - 日付
  - 受注番号
  - ユーザー様
  - ステータス
  - 希望納期
  - 確認先
  - 回答納期
  - 最短◎発送日
  - 備考（理由）
  - 履歴
- カンバン / テーブル切り替え
- フリーワード検索
- ステータス絞り込み
- 回答納期ベースの絞り込み
- カードのドラッグ＆ドロップ移動
- コメント、チェックリスト、アクティビティ
- SQLite 永続化と初期シードデータ

起動手順:

1. バックエンド

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

2. フロントエンド

PowerShell で実行ポリシーに引っかかる場合は `npm` ではなく `npm.cmd` を使います。

```bash
cd frontend
npm.cmd install
npm.cmd run dev
```

- API: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

使い方:

- 各列下部の入力欄から案件を追加できます
- 上部の検索バーで `受注番号`、`ユーザー様`、`確認先`、`備考` を検索できます
- `カンバン` と `テーブル` を切り替えて閲覧できます
- 案件カードやテーブル行をクリックすると詳細モーダルを開けます
- 詳細モーダルでは案件項目を編集して保存できます

## misumi_types スクリプト

既存スクリプト群は [tools/misumi_types/README.md](C:\Users\A000594001\my-project\tools\misumi_types\README.md) にまとめています。設定ファイル、ログ、`archive` 内の退避版も同じ配下に集約しています。

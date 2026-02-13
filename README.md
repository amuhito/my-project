# misumi_types scripts

## 実行エントリポイント
- **唯一の実行入口**: `execute_scripts_with_step7.py`
- 実行時は `config.ini` の `[scripts]` を上から順に読み、`script_1`, `script_2`, ... を実行します。

## 実行手順（Windows想定）
1. `config.ini` の `[paths]` と `[scripts]` を確認・更新する。
2. 必要な依存（既存運用のもの）を準備する。
3. 以下を実行する。
   ```bat
   python execute_scripts_with_step7.py
   ```
4. ログは `script_execution.log` を確認する。

## フォルダ構成（最小）
- `execute_scripts_with_step7.py`: 実行制御（エントリポイント）
- `config.ini`: パス・実行順・モード設定
- `*.py`: 各処理スクリプト本体
- `archive/`: 旧 `*_patched*.py` の退避先（直接実行しない）

## 運用ルール（patched増殖防止）
- `*_patched*.py` は新規作成しない。
- 修正は**元ファイルを直接更新**する。
- 一時退避が必要な場合のみ `archive/` に移動し、`config.ini` の `[scripts]` から参照しない。

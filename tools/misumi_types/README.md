# misumi_types

既存の Python / PowerShell スクリプトをまとめたディレクトリです。ルート直下で混在していた実行ファイル、設定、ログ、退避ファイルをここに整理しました。

## 含まれるもの

- `execute_scripts_with_step7.py`
  メイン実行スクリプト
- `config.ini`
  パスや実行順を定義する設定
- `*.py`
  補助スクリプト群
- `resize_explorer.ps1`
  PowerShell 補助スクリプト
- `script_execution.log`
  実行ログ
- `archive/`
  patched 版などの退避ファイル

## 補足

- `config.ini` の `script_folder` は、このリポジトリ内の `tools/misumi_types` を指すように更新しています
- 実行時に参照する `input_folder` / `output_folder` / `source_folder` は利用環境に合わせて調整してください

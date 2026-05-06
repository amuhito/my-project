# Repository Organization Plan

この文書は、`my-project` を段階的に整理するための方針です。

## 背景

現在のリポジトリには、複数のPoCアプリ、ローカル起動補助、既存スクリプトがトップレベルに並んでいます。
短期的には問題なく動きますが、今後PoCが増えると、どれがアプリ本体でどれが補助ファイルか分かりにくくなります。

## 目標構成

最終的には、次のような構成へ寄せることを目標にします。

```text
apps/
  delivery-kanban/
  machine-process-visibility/

scripts/
  delivery-kanban-local/

tools/
  misumi_types/

docs/
  repo-organization.md
  development.md

README.md
```

## 段階的な進め方

### Phase 1: 入口ドキュメント整理

- ルートREADMEで各ディレクトリの役割を明確にする。
- 各PoCのREADMEに起動方法、検証方法、ログイン情報を明記する。
- ディレクトリ移動はしない。

### Phase 2: アプリごとの境界整理

- 各PoCのREADME、`.gitignore`、起動方法、テスト方法を揃える。
- 補助スクリプトがどのアプリ専用かを明記する。
- 共通化できる運用手順があれば `docs/` に移す。
- この段階でも、まだディレクトリ移動はしない。

### Phase 3: ディレクトリ移動

- `delivery-kanban-poc/` を `apps/delivery-kanban/` へ移す。
- `machine-process-visibility-poc/` を `apps/machine-process-visibility/` へ移す。
- `delivery-kanban-poc-local/` を `scripts/delivery-kanban-local/` へ移す。
- README、スクリプト、Docker設定、相対パスを合わせて修正する。

## 注意点

- 機能追加PRと大規模なディレクトリ移動は分ける。
- 移動PRでは、できるだけコード内容を変えずパス変更に集中する。
- 起動手順と検証コマンドをPR本文に必ず記載する。

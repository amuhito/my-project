# AWS App Runner 補足

2026年4月10日時点で AWS の公式資料には日付差分があります。

- API リファレンスの一部: `2026年3月31日` から新規利用者向けに終了
- 可用性変更の案内ページ: `2026年4月30日` から新規利用者向けにクローズ

参考:
- [AWS App Runner `StartDeployment` API](https://docs.aws.amazon.com/apprunner/latest/api/API_StartDeployment.html)
- [AWS App Runner availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)

そのため、この POC を今から AWS 上へ新規に見せる目的で載せるなら、まずは Lightsail Container Service を優先するのが現実的です。

もし既存の App Runner 利用アカウントが社内にある場合は、この `Dockerfile` を使って App Runner のイメージデプロイ構成へ持っていくこともできます。

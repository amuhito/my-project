# AWS Lightsail 配置手順

この手順は、2026年4月10日時点で新規に AWS 上へこの POC を載せる最小構成です。

## 前提

- AWS アカウントがある
- Docker がローカルで使える
- AWS CLI v2 が使える
- リージョンは例として `ap-northeast-1` を使う

参考:
- [Amazon Lightsail のコンテナサービス概要](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html)
- [Lightsail にローカルイメージを push する方法](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-pushing-container-images.html)
- [AWS CLI `push-container-image`](https://docs.aws.amazon.com/cli/latest/reference/lightsail/push-container-image.html)
- [AWS CLI `create-container-service-deployment`](https://docs.aws.amazon.com/cli/latest/reference/lightsail/create-container-service-deployment.html)

## 1. Docker イメージを作る

```bash
cd /path/to/delivery-kanban-poc
docker build -t delivery-kanban-poc:latest .
```

## 2. Lightsail コンテナサービスを作る

まず AWS CLI の認証を済ませます。

```bash
aws configure
```

次にコンテナサービスを作ります。

```bash
aws lightsail create-container-service \
  --service-name delivery-kanban-poc \
  --power nano \
  --scale 1 \
  --region ap-northeast-1
```

`power` は POC なら `nano` か `micro` から開始で十分です。

## 3. イメージを Lightsail へ push する

```bash
aws lightsail push-container-image \
  --service-name delivery-kanban-poc \
  --label app \
  --image delivery-kanban-poc:latest \
  --region ap-northeast-1
```

実行結果に、Lightsail 側へ登録されたイメージ名が出ます。
例:

```text
:delivery-kanban-poc.app.1
```

この値を次の手順で使います。

## 4. デプロイ定義を作る

[deployment/aws/lightsail-containers.json](../deployment/aws/lightsail-containers.json) の `IMAGE_NAME` を、push 結果のイメージ名に置き換えます。

必要なら `KANBAN_CORS_ORIGINS` も実 URL に変えてください。

## 5. デプロイする

```bash
aws lightsail create-container-service-deployment \
  --service-name delivery-kanban-poc \
  --containers file://deployment/aws/lightsail-containers.json \
  --public-endpoint file://deployment/aws/lightsail-public-endpoint.json \
  --region ap-northeast-1
```

## 6. 動作確認

Lightsail コンソール上で公開 URL を確認して、次を見ます。

- `/` で画面が開くか
- `/api/health` が `{"status":"ok"}` を返すか
- カード一覧が表示されるか

## 補足

- 今回は SQLite のままなので、コンテナ再作成時のデータ保持は弱いです
- 継続利用するなら、次の段階で PostgreSQL への移行を推奨します
- まずはダミーデータで関係者レビュー用に使う想定です

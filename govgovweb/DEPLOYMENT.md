# 本番環境デプロイ手順

このドキュメントでは、WebアプリケーションとFlask APIをCloud Runにデプロイする手順を説明します。

## アーキテクチャ

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  ユーザー   │─────>│  Next.js Web App │─────>│   Flask API      │
│  Browser    │      │  (Cloud Run)     │      │  (Cloud Run)     │
└─────────────┘      └──────────────────┘      └──────────────────┘
                              │                          │
                              │                          ▼
                              │                  ┌──────────────────┐
                              │                  │ Vertex AI RAG    │
                              │                  │ Vertex AI Search │
                              │                  └──────────────────┘
                              ▼
                     ┌──────────────────┐
                     │  Static Assets   │
                     └──────────────────┘
```

## 前提条件

- Google Cloud SDK (`gcloud`) がインストール済み
- プロジェクトID: `govgov-473916`
- 必要なAPIが有効化済み:
  - Cloud Run API
  - Artifact Registry API
  - Vertex AI API
  - Secret Manager API

## ステップ1: 環境変数をSecret Managerに設定

### 1.1 Flask API用の環境変数

```bash
# RAG Corpus リソース名
gcloud secrets create rag-corpus-resource-name \
  --data-file=- <<EOF
projects/govgov-473916/locations/us-east4/ragCorpora/2305843009213693952
EOF

# Vertex AI Searchデータストア ID
gcloud secrets create vertex-ai-search-datastore-id \
  --data-file=- <<EOF
datastore-govgov_1759561195262
EOF

# Twitter APIキー（既存のものを使用）
# すでに設定済みの場合はスキップ
```

### 1.2 Next.js用の環境変数

```bash
# Flask APIのURL（後でCloud RunのURLに置き換え）
gcloud secrets create webapp-backend-api-url \
  --data-file=- <<EOF
https://[FLASK_API_SERVICE_URL]
EOF
```

## ステップ2: Flask APIをCloud Runにデプロイ

### 2.1 requirements.txtに依存関係を追加

`requirements.txt`に以下が含まれていることを確認:
```
tenacity
```

### 2.2 Flask APIをデプロイ

```bash
# プロジェクトルートから実行
gcloud run deploy factcheck-bot \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=govgov-473916 \
  --set-env-vars RAG_LOCATION=us-east4 \
  --set-env-vars MODEL_LOCATION=us-central1 \
  --set-env-vars MODEL_NAME=gemini-2.0-flash-exp \
  --set-env-vars VERTEX_AI_SEARCH_LOCATION=global \
  --set-env-vars TEMPERATURE=0.7 \
  --set-env-vars MAX_OUTPUT_TOKENS=2048 \
  --set-env-vars SIMILARITY_TOP_K=10 \
  --set-env-vars GRPC_DNS_RESOLVER=native \
  --set-secrets RAG_CORPUS_RESOURCE_NAME=rag-corpus-resource-name:latest \
  --set-secrets VERTEX_AI_SEARCH_DATA_STORE_ID=vertex-ai-search-datastore-id:latest \
  --memory 1Gi \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --project govgov-473916
```

### 2.3 デプロイ後のURL取得

```bash
# Flask APIのURLを取得
FLASK_API_URL=$(gcloud run services describe factcheck-bot \
  --region asia-northeast1 \
  --format 'value(status.url)' \
  --project govgov-473916)

echo "Flask API URL: $FLASK_API_URL"
```

## ステップ3: Next.js WebアプリをCloud Runにデプロイ

### 3.1 webapp/.env.productionを作成

```bash
cd webapp
cat > .env.production <<EOF
BACKEND_API_URL=$FLASK_API_URL
EOF
```

### 3.2 Next.jsアプリをデプロイ

```bash
# webappディレクトリから実行
cd webapp

gcloud run deploy govgovweb \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars BACKEND_API_URL=$FLASK_API_URL \
  --memory 512Mi \
  --timeout 60 \
  --max-instances 10 \
  --min-instances 0 \
  --project govgov-473916
```

### 3.3 デプロイ後のURL取得

```bash
# WebアプリのURLを取得
WEBAPP_URL=$(gcloud run services describe govgovweb \
  --region asia-northeast1 \
  --format 'value(status.url)' \
  --project govgov-473916)

echo "Web App URL: $WEBAPP_URL"
```

## ステップ4: 動作確認

### 4.1 Flask APIのヘルスチェック

```bash
curl $FLASK_API_URL/healthz
# 期待される応答: {"health":"ok","ok":true}
```

### 4.2 Flask API経由でRAGをテスト

```bash
curl -X POST $FLASK_API_URL/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"デジタル庁の令和5年度予算について教えてください"}' \
  | jq .
```

### 4.3 WebアプリのUIテスト

ブラウザで以下にアクセス:
```
$WEBAPP_URL
```

チャットUIから質問を入力して、回答が返ることを確認。

## ステップ5: カスタムドメイン設定（オプション）

### 5.1 ドメインマッピング

```bash
# Webアプリにカスタムドメインをマッピング
gcloud run domain-mappings create \
  --service govgovweb \
  --domain your-domain.com \
  --region asia-northeast1

# DNSレコードを設定（出力されたCNAMEを追加）
```

## トラブルシューティング

### 問題: gRPC DNS解決エラー

**症状**:
```
DNS resolution failed for *.googleapis.com
```

**解決策**:
環境変数に以下を追加:
```bash
--set-env-vars GRPC_DNS_RESOLVER=native
```

### 問題: メモリ不足エラー

**症状**:
```
Container failed to allocate memory
```

**解決策**:
メモリを増やす:
```bash
gcloud run services update factcheck-bot --memory 2Gi --region asia-northeast1 --project govgov-473916
```

### 問題: タイムアウトエラー

**症状**:
```
Request timeout
```

**解決策**:
タイムアウトを延長:
```bash
gcloud run services update factcheck-bot --timeout 600 --region asia-northeast1 --project govgov-473916
```

## コスト最適化

### オートスケーリング設定

```bash
# 最小インスタンス数を0に設定（アクセスがない時はコスト0）
gcloud run services update factcheck-bot --min-instances 0 --region asia-northeast1 --project govgov-473916

# 最大インスタンス数を制限（予想外の高額請求を防ぐ）
gcloud run services update factcheck-bot --max-instances 10 --region asia-northeast1 --project govgov-473916
```

### 同時実行数の調整

```bash
# 1インスタンスあたりの同時実行数を増やす（インスタンス数削減）
gcloud run services update factcheck-bot --concurrency 80 --region asia-northeast1 --project govgov-473916
```

## セキュリティ強化

### 認証の追加

```bash
# WebアプリのみパブリックアクセスOK、Flask APIは内部通信のみに制限
gcloud run services update factcheck-bot --no-allow-unauthenticated --region asia-northeast1 --project govgov-473916

# WebアプリからFlask APIへのアクセスにService Accountを使用
# (Next.js Edge Runtimeの制約により、別途検討が必要)
```

## 継続的デプロイ (CI/CD)

### Cloud Buildを使った自動デプロイ

`cloudbuild.yaml`を作成:

```yaml
steps:
  # Flask APIのビルドとデプロイ
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'factcheck-bot'
      - '--source=.'
      - '--region=asia-northeast1'
      - '--platform=managed'

  # Next.jsのビルドとデプロイ
  - name: 'gcr.io/cloud-builders/gcloud'
    dir: 'webapp'
    args:
      - 'run'
      - 'deploy'
      - 'govgovweb'
      - '--source=.'
      - '--region=asia-northeast1'
      - '--platform=managed'
```

GitHubと連携:
```bash
gcloud builds triggers create github \
  --repo-name=govgov \
  --repo-owner=HKobayashi2003 \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

## モニタリング

### ログの確認

```bash
# Flask APIのログ
gcloud run services logs read factcheck-bot --region asia-northeast1 --project govgov-473916

# Webアプリのログ
gcloud run services logs read govgovweb --region asia-northeast1 --project govgov-473916
```

### メトリクスの確認

Cloud Consoleで以下を確認:
- リクエスト数
- レイテンシー
- エラー率
- CPU/メモリ使用率

URL: https://console.cloud.google.com/run

## まとめ

以上の手順で、WebアプリケーションとFlask APIがCloud Runにデプロイされ、本番環境で稼働します。

**デプロイ後のURL**:
- Flask API: `https://factcheck-bot-67tdojz6sq-an.a.run.app`
- Web App: `https://govgovweb-67tdojz6sq-an.a.run.app`

質問や問題が発生した場合は、上記のトラブルシューティングセクションを参照してください。

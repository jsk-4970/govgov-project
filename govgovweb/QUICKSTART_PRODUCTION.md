# 本番環境クイックスタートガイド

最速で本番環境（Cloud Run）にデプロイするための簡潔なガイドです。

## 🚀 5ステップでデプロイ

### ステップ1: 認証とプロジェクト設定

```bash
# GCPにログイン
gcloud auth login

# プロジェクトを設定
gcloud config set project govgov-473916

# Application Default Credentials を設定
gcloud auth application-default login
```

### ステップ2: 必要なAPIを有効化

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

### ステップ3: 環境変数をSecret Managerに保存

```bash
# RAG Corpus リソース名
echo "projects/govgov-473916/locations/us-east4/ragCorpora/2305843009213693952" | \
  gcloud secrets create rag-corpus-resource-name --data-file=-

# Vertex AI Searchデータストア ID
echo "datastore-govgov_1759561195262" | \
  gcloud secrets create vertex-ai-search-datastore-id --data-file=-
```

### ステップ4: Flask APIをデプロイ

```bash
# プロジェクトルートから実行
gcloud run deploy factcheck-bot \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=govgov-473916,RAG_LOCATION=us-east4,MODEL_LOCATION=us-central1,MODEL_NAME=gemini-2.0-flash-exp,VERTEX_AI_SEARCH_LOCATION=global,TEMPERATURE=0.7,MAX_OUTPUT_TOKENS=2048,SIMILARITY_TOP_K=10,GRPC_DNS_RESOLVER=native \
  --set-secrets RAG_CORPUS_RESOURCE_NAME=rag-corpus-resource-name:latest,VERTEX_AI_SEARCH_DATA_STORE_ID=vertex-ai-search-datastore-id:latest \
  --memory 1Gi \
  --timeout 300
```

**デプロイ完了後、URLを控える:**
```bash
FLASK_API_URL=$(gcloud run services describe factcheck-bot --region asia-northeast1 --format 'value(status.url)')
echo "Flask API URL: $FLASK_API_URL"
```

### ステップ5: Next.js Webアプリをデプロイ

```bash
# webappディレクトリに移動
cd webapp

# デプロイ
gcloud run deploy govgovweb \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars BACKEND_API_URL=$FLASK_API_URL \
  --memory 512Mi \
  --timeout 60
```

**デプロイ完了後、URLを控える:**
```bash
WEBAPP_URL=$(gcloud run services describe govgovweb --region asia-northeast1 --format 'value(status.url)')
echo "✅ Web App URL: $WEBAPP_URL"
```

---

## ✅ 動作確認

### 1. Flask APIの確認

```bash
# ヘルスチェック
curl $FLASK_API_URL/healthz

# RAG機能のテスト
curl -X POST $FLASK_API_URL/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"デジタル庁の予算について"}' | jq .
```

### 2. Webアプリの確認

ブラウザで以下にアクセス:
```
$WEBAPP_URL
```

チャットUIから質問を入力して回答が表示されることを確認。

---

## 🔧 トラブルシューティング

### エラー: "DNS resolution failed"

**解決策**: 環境変数に `GRPC_DNS_RESOLVER=native` が設定されているか確認。

```bash
gcloud run services update factcheck-bot \
  --update-env-vars GRPC_DNS_RESOLVER=native
```

### エラー: "Memory limit exceeded"

**解決策**: メモリを増やす。

```bash
gcloud run services update factcheck-bot --memory 2Gi
```

### エラー: "Timeout"

**解決策**: タイムアウトを延長。

```bash
gcloud run services update factcheck-bot --timeout 600
```

---

## 📊 デプロイ後の管理

### ログの確認

```bash
# Flask APIのログ
gcloud run services logs read factcheck-bot --region asia-northeast1 --limit 50

# Webアプリのログ
gcloud run services logs read govgovweb --region asia-northeast1 --limit 50
```

### サービスの削除

```bash
# 不要になった場合
gcloud run services delete factcheck-bot --region asia-northeast1
gcloud run services delete govgovweb --region asia-northeast1
```

---

## 💰 コスト見積もり

**Cloud Run料金** (asia-northeast1リージョン):
- リクエスト: 100万リクエストまで無料
- CPU時間: 月18万vCPU秒まで無料
- メモリ: 月32万GiB秒まで無料

**Vertex AI料金**:
- Gemini 2.0 Flash: 入力$0.075/1Mトークン、出力$0.30/1Mトークン
- RAG Engine: ストレージ料金が別途発生

**想定コスト（月1,000リクエストの場合）**:
- Cloud Run: ほぼ無料（無料枠内）
- Vertex AI: 約$5-10（使用量による）

---

## 🎯 次のステップ

1. **カスタムドメイン設定**: 独自ドメインをマッピング
2. **CI/CD設定**: GitHub Actionsで自動デプロイ
3. **モニタリング設定**: Cloud Monitoringでアラート設定
4. **セキュリティ強化**: IAM認証、HTTPS強制

詳細は [DEPLOYMENT.md](./DEPLOYMENT.md) を参照してください。

---

## 📞 サポート

問題が発生した場合:
1. Cloud Consoleのログを確認
2. [DEPLOYMENT.md](./DEPLOYMENT.md) のトラブルシューティングセクションを参照
3. GitHubのIssueを作成

**Cloud Run Console**: https://console.cloud.google.com/run?project=govgov-473916

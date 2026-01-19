# govgov-473916 プロジェクト復元ガイド

削除日: 2026-01-15

## 削除されたリソース一覧

### Cloud Run サービス (7つ)
| サービス名 | リージョン | 復元方法 |
|-----------|-----------|---------|
| estat-etl | asia-northeast1 | ソースから再デプロイ |
| extract-company-info | asia-northeast1 | Cloud Functions として再デプロイ |
| factcheck-api | asia-northeast1 | ソースから再デプロイ |
| factcheck-bot | asia-northeast1 | govgovbot/ から再デプロイ |
| get-info-from-url | asia-northeast1 | Cloud Functions として再デプロイ |
| get-url-from-company | asia-northeast1 | Cloud Functions として再デプロイ |
| govgovweb | asia-northeast1 | govgovweb/ から再デプロイ |

### Cloud Storage バケット (11個)
| バケット名 | 復元期限 | 復元コマンド |
|-----------|---------|-------------|
| govgov-473916-data | 7日以内 (2026-01-22まで) | Soft Delete から復元可能 |
| govgov-473916-estat-data | 7日以内 | Soft Delete から復元可能 |
| govgov-473916_cloudbuild | 7日以内 | 再作成で対応 |
| govgov-state-335117605715 | 7日以内 | Soft Delete から復元可能 |
| rsdata_govgov | 7日以内 | Soft Delete から復元可能 |
| run-sources-govgov-473916-asia-northeast1 | 7日以内 | 再作成で対応 |
| 335117605715_asia_northeast1_import | 7日以内 | 再作成で対応 |
| 335117605715_asia_northeast1_import_custom | 7日以内 | 再作成で対応 |
| 335117605715_asia_northeast1_import_document | 7日以内 | 再作成で対応 |
| gcf-v2-sources-335117605715-asia-northeast1 | 7日以内 | 再作成で対応 |
| gcf-v2-uploads-335117605715.asia-northeast1.cloudfunctions.appspot.com | 7日以内 | 再作成で対応 |

### Vertex AI RAG Corpus (1つ)
| 名前 | リージョン | 復元方法 |
|-----|-----------|---------|
| corpus_govgov | us-east4 | 再作成が必要 |

---

## 復元手順

### 1. Cloud Storage バケットの復元 (Soft Delete)

削除から7日以内であれば、以下のコマンドで復元可能です。

```bash
# プロジェクトを設定
gcloud config set project govgov-473916

# Soft Delete されたバケットを一覧表示
gcloud storage ls --soft-deleted

# 特定のバケットを復元
gcloud storage buckets restore gs://govgov-473916-data

# バケット内のオブジェクトを復元
gcloud storage objects restore "gs://govgov-473916-data/**" --all-versions
```

### 2. Cloud Run サービスの再デプロイ

#### govgovbot (factcheck-bot)
```bash
cd govgovbot
gcloud run deploy factcheck-bot \
  --source . \
  --region asia-northeast1 \
  --project govgov-473916 \
  --allow-unauthenticated
```

#### govgovweb
```bash
cd govgovweb
gcloud run deploy govgovweb \
  --source . \
  --region asia-northeast1 \
  --project govgov-473916 \
  --allow-unauthenticated
```

### 3. Vertex AI RAG Corpus の再作成

```bash
# RAG Corpus を作成
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://us-east4-aiplatform.googleapis.com/v1/projects/govgov-473916/locations/us-east4/ragCorpora" \
  -d '{
    "displayName": "corpus_govgov",
    "vectorDbConfig": {
      "ragManagedDb": {},
      "ragEmbeddingModelConfig": {
        "vertexPredictionEndpoint": {
          "endpoint": "projects/govgov-473916/locations/us-east4/publishers/google/models/text-multilingual-embedding-002"
        }
      }
    }
  }'
```

作成後、.env ファイルの `RAG_CORPUS_ID` と `RAG_CORPUS_RESOURCE_NAME` を更新してください。

### 4. データの再インデックス

RAG Corpus にデータを再インデックスするには:

```bash
# govgov-473916-data バケットを復元後
# RAG にファイルをインポート
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://us-east4-aiplatform.googleapis.com/v1/projects/govgov-473916/locations/us-east4/ragCorpora/{NEW_CORPUS_ID}/ragFiles:import" \
  -d '{
    "importRagFilesConfig": {
      "gcsSource": {
        "uris": ["gs://govgov-473916-data/**"]
      }
    }
  }'
```

---

## 環境変数の更新

復元後、`govgovbot/.env` を以下のように更新してください:

```env
PROJECT_ID=govgov-473916
LOCATION=global
BUCKET_NAME=govgov-473916-data

# Vertex AI RAG Engine (新しいCorpus ID で更新)
RAG_CORPUS_ID=<新しいCORPUS_ID>
RAG_LOCATION=us-east4
RAG_CORPUS_RESOURCE_NAME=projects/govgov-473916/locations/us-east4/ragCorpora/<新しいCORPUS_ID>
MODEL_LOCATION=global
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=8192
SIMILARITY_TOP_K=10

# Vertex AI Search
VERTEX_AI_SEARCH_DATA_STORE_ID=datastore-govgov_1759561195262
VERTEX_AI_SEARCH_LOCATION=global

# gRPC設定
GRPC_DNS_RESOLVER=native
GRPC_VERBOSITY=ERROR
```

---

## 注意事項

1. **Soft Delete の有効期限**: 削除から7日間のみ復元可能
2. **RAG Corpus**: 再作成が必要。Corpus ID が変わるため、.env の更新が必須
3. **Cloud Run**: ソースコードから再デプロイ可能。URL は変わる可能性あり
4. **Firestore/Firebase**: 今回の削除対象外。データは保持されています

---

## 問い合わせ

復元に問題がある場合は、Google Cloud Console から確認してください:
- https://console.cloud.google.com/run?project=govgov-473916
- https://console.cloud.google.com/storage/browser?project=govgov-473916

# e-Stat API ETL パイプライン

e-Stat（政府統計の総合窓口）APIから統計データを取得し、JSONL形式でGoogle Cloud Storageに保存するサーバーレスETLパイプラインです。

## 📋 機能概要

1. **統計表リスト取得**: e-Stat APIの`getStatsList`を使用して全統計表IDを取得（ページネーション対応）
2. **統計データ取得**: 各統計表IDに対して`getStatsData`を呼び出してデータ取得
3. **JSONL変換**: 取得したデータをJSONL（JSON Lines）形式に変換
4. **GCS保存**: 日付ごとのフォルダに整理してCloud Storageに保存
5. **実行サマリー**: 処理結果のサマリーをJSON形式で保存

## 🏗️ アーキテクチャ

```
e-Stat API → estat_client.py → gcs_uploader.py → Google Cloud Storage
                                      ↓
                            Secret Manager (APIキー取得)
```

### 主要コンポーネント

| ファイル | 説明 |
|---------|------|
| [main.py](main.py) | ETLオーケストレーション処理 |
| [src/common/estat_client.py](../../src/common/estat_client.py) | e-Stat APIクライアント |
| [src/common/gcs_uploader.py](../../src/common/gcs_uploader.py) | GCSアップローダー |
| [src/common/secret_manager.py](../../src/common/secret_manager.py) | Secret Manager統合 |

## 📦 出力データ構造

GCS上の以下のパスにファイルが保存されます:

```
gs://your-bucket/
└── estat-data/
    └── 2025-01-15/           # 実行日付
        ├── 0000000001.jsonl  # 統計表ID.jsonl
        ├── 0000000002.jsonl
        ├── ...
        └── _summary.json     # 実行サマリー
```

### JSONLフォーマット

各統計表のデータは1行1レコードのJSONL形式で保存されます:

```jsonl
{"@tab":"01","@cat01":"001","@area":"00000","@time":"2020","@unit":"人","$":"1234567"}
{"@tab":"01","@cat01":"002","@area":"00000","@time":"2020","@unit":"人","$":"2345678"}
```

**フィールド説明:**
- `@tab`: 表章事項コード
- `@cat01`: 分類事項コード
- `@area`: 地域事項コード
- `@time`: 時間軸事項コード
- `@unit`: 単位
- `$`: 統計数値

## 🚀 セットアップ

### 1. e-Stat APIキーの取得

1. [e-Stat API利用登録ページ](https://www.e-stat.go.jp/api/)でアカウント登録
2. アプリケーションIDを取得
3. Google Secret Managerに登録:

```bash
# APIキーをSecret Managerに登録
echo -n "YOUR_ESTAT_APP_ID" | gcloud secrets create estat-app-id \
    --data-file=- \
    --project=govgov-473916
```

### 2. GCP環境設定

```bash
# プロジェクトIDを設定
export PROJECT_ID="govgov-473916"

# 必要なAPIを有効化
gcloud services enable \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    --project=$PROJECT_ID

# GCSバケット作成
gsutil mb -p $PROJECT_ID -l asia-northeast1 gs://${PROJECT_ID}-estat-data

# サービスアカウント作成
gcloud iam service-accounts create estat-etl \
    --display-name="e-Stat ETL Service Account" \
    --project=$PROJECT_ID

# 必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:estat-etl@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:estat-etl@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### 3. ローカル実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# Application Default Credentials設定
gcloud auth application-default login

# 環境変数設定
export PROJECT_ID="govgov-473916"
export BUCKET_NAME="govgov-473916-estat-data"
export ESTAT_APP_ID_SECRET="estat-app-id"

# テスト実行（最初の10件のみ処理）
export MAX_STATS_COUNT=10
python main.py
```

## ☁️ クラウドへのデプロイ

### Cloud Functionsへのデプロイ

```bash
# デプロイ
gcloud functions deploy estat-etl \
    --gen2 \
    --runtime=python311 \
    --region=asia-northeast1 \
    --source=. \
    --entry-point=cloud_function_entry \
    --trigger-http \
    --no-allow-unauthenticated \
    --service-account=estat-etl@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-env-vars PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${PROJECT_ID}-estat-data \
    --timeout=3600s \
    --memory=512MB \
    --project=$PROJECT_ID

# Cloud Schedulerで定期実行設定（毎日深夜2時）
gcloud scheduler jobs create http estat-etl-daily \
    --location=asia-northeast1 \
    --schedule="0 2 * * *" \
    --uri="https://asia-northeast1-${PROJECT_ID}.cloudfunctions.net/estat-etl" \
    --http-method=POST \
    --oidc-service-account-email=estat-etl@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=$PROJECT_ID
```

### Cloud Runへのデプロイ

```bash
# イメージビルド＆デプロイ
gcloud run deploy estat-etl \
    --source=. \
    --platform=managed \
    --region=asia-northeast1 \
    --service-account=estat-etl@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-env-vars PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${PROJECT_ID}-estat-data \
    --timeout=3600 \
    --memory=1Gi \
    --no-allow-unauthenticated \
    --project=$PROJECT_ID

# Cloud Schedulerで定期実行
gcloud scheduler jobs create http estat-etl-daily-run \
    --location=asia-northeast1 \
    --schedule="0 2 * * *" \
    --uri="https://estat-etl-xxxxx-an.a.run.app" \
    --http-method=POST \
    --oidc-service-account-email=estat-etl@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=$PROJECT_ID
```

## ⚙️ 環境変数

| 変数名 | 説明 | 必須 | デフォルト値 |
|--------|------|------|--------------|
| `PROJECT_ID` | GCPプロジェクトID | ✅ | - |
| `BUCKET_NAME` | 出力先GCSバケット名 | ✅ | - |
| `ESTAT_APP_ID_SECRET` | Secret ManagerのシークレットID | | `estat-app-id` |
| `MAX_STATS_COUNT` | 処理する統計表の最大数（テスト用） | | 無制限 |

## 📊 API仕様

### e-Stat API v3.0

- **公式ドキュメント**: https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0
- **ベースURL**: `https://api.e-stat.go.jp/rest/3.0/app`
- **レート制限**: 明示的な制限なし（本実装では1秒/リクエストで制御）

### 主要エンドポイント

#### getStatsList (統計表情報取得)

```
GET /rest/3.0/app/json/getStatsList
```

**パラメータ:**
- `appId` (必須): アプリケーションID
- `startPosition`: データ取得開始位置
- `limit`: 取得件数上限
- `searchKind`: データ種別（1: 統計情報, 2: 小地域）

#### getStatsData (統計データ取得)

```
GET /rest/3.0/app/json/getStatsData
```

**パラメータ:**
- `appId` (必須): アプリケーションID
- `statsDataId` (必須): 統計表ID
- `metaGetFlg`: メタ情報取得フラグ（Y/N）
- `cntGetFlg`: データ件数取得フラグ（Y/N）

## 🔧 エラーハンドリング

- **APIエラー**: リトライ処理（最大3回、指数バックオフ）
- **個別統計表のエラー**: ログ出力して次の統計表の処理を継続
- **実行サマリー**: 成功数・失敗数・失敗した統計表IDのリストを保存

### エラーコード

| コード | 説明 |
|-------|------|
| 0-2 | 正常終了 |
| 100 | 認証失敗 |
| 200 | データベースアクセスエラー |
| 300 | データ不存在 |

## 📝 ログ

構造化ログ（JSON形式）でCloud Loggingに出力:

```json
{
  "severity": "INFO",
  "timestamp": "2025-01-15T02:00:00Z",
  "message": "Processing 1/1000: 0000000001",
  "module": "main"
}
```

## 💰 コスト見積もり

- **Cloud Functions**: 実行時間に応じて課金（毎日1回・1時間実行で月額 $5-10程度）
- **Cloud Storage**: ストレージ容量に応じて課金（データ量次第）
- **Cloud Scheduler**: ジョブ数に応じて課金（$0.10/ジョブ/月）

## 🐛 トラブルシューティング

### 認証エラー

```
Failed to fetch secret estat-app-id: 403 Permission denied
```

**対処法**: サービスアカウントに `roles/secretmanager.secretAccessor` 権限を付与

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:estat-etl@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### タイムアウト

```
Function execution took 540000 ms, finished with status: 'timeout'
```

**対処法**: `--timeout` を増やす、または `MAX_STATS_COUNT` でデータ件数を制限

### Secret Managerからのキー取得失敗

```
Failed to fetch secret estat-app-id: Secret not found
```

**対処法**: Secret Managerにe-Stat APIキーを登録

```bash
echo -n "YOUR_ESTAT_APP_ID" | gcloud secrets create estat-app-id \
    --data-file=- \
    --project=$PROJECT_ID
```

## 🧪 開発

### 型チェック

```bash
mypy src/common/estat_client.py src/common/gcs_uploader.py src/common/secret_manager.py
```

### コードフォーマット

```bash
black src/common/*.py data/estat/main.py
isort src/common/*.py data/estat/main.py
```

### テスト実行

```bash
pytest tests/common/
```

## 📚 参考資料

- [e-Stat API仕様書 v3.0](https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0)
- [Google Cloud Functions ドキュメント](https://cloud.google.com/functions/docs)
- [Google Cloud Storage Python SDK](https://cloud.google.com/storage/docs/reference/libraries#client-libraries-install-python)
- [Google Secret Manager Python SDK](https://cloud.google.com/secret-manager/docs/reference/libraries#client-libraries-install-python)
- [政府統計の総合窓口（e-Stat）](https://www.e-stat.go.jp/)

## 📄 ライセンス

このプロジェクトはMITライセンスで公開されています。

# GCP環境セットアップガイド

このドキュメントでは、プロジェクトに必要なGoogle Cloud Platform (GCP) の環境構築手順を説明します。

## 前提条件

- Googleアカウント
- クレジットカード（GCPの無料枠を使用する場合でも必要）
- Google Cloud SDK (gcloud CLI) がインストール済み

## ステップ1: GCPプロジェクトの作成

### 1.1 Google Cloud Consoleにアクセス

[Google Cloud Console](https://console.cloud.google.com/) にアクセスし、Googleアカウントでログインします。

### 1.2 新しいプロジェクトを作成

1. 画面上部の「プロジェクトを選択」をクリック
2. 「新しいプロジェクト」をクリック
3. プロジェクト名を入力（例: `factcheck-bot-dev`）
4. プロジェクトIDをメモ（例: `factcheck-bot-dev-123456`）
5. 「作成」をクリック

### 1.3 請求先アカウントの設定

無料枠を使用する場合でも、請求先アカウントの設定が必要です。

1. ナビゲーションメニュー > 「お支払い」
2. 請求先アカウントをリンク

## ステップ2: 必要なAPIの有効化

以下のAPIを有効化します。

```bash
# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID

# 必要なAPIを有効化
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable discoveryengine.googleapis.com
```

または、GCPコンソールから手動で有効化:

1. ナビゲーションメニュー > 「APIとサービス」 > 「ライブラリ」
2. 以下を検索して「有効にする」をクリック:
   - Vertex AI API
   - Cloud Storage API
   - Secret Manager API
   - Discovery Engine API (Vertex AI Search用)

## ステップ3: gcloud CLIの初期設定

### 3.1 gcloud の初期化

```bash
# gcloudの初期設定
gcloud init

# プロンプトに従って:
# 1. Googleアカウントでログイン
# 2. 作成したプロジェクトを選択
# 3. デフォルトのリージョンを選択（推奨: asia-northeast1 = 東京）
```

### 3.2 アプリケーションデフォルト認証情報の設定

ローカル開発でGCP APIを使用するための認証設定:

```bash
gcloud auth application-default login
```

ブラウザが開くので、Googleアカウントでログインし、権限を許可します。

### 3.3 デフォルトリージョンの設定

```bash
# リージョンを設定（東京リージョン）
gcloud config set compute/region asia-northeast1
gcloud config set compute/zone asia-northeast1-a
```

## ステップ4: Cloud Storage バケットの作成

行政事業レビューデータを保存するためのバケットを作成します。

```bash
# バケット名を設定（グローバルで一意である必要があります）
export BUCKET_NAME="factcheck-bot-data-YOUR_UNIQUE_ID"

# バケットを作成
gcloud storage buckets create gs://${BUCKET_NAME} \
  --location=asia-northeast1 \
  --uniform-bucket-level-access

# 確認
gcloud storage buckets list
```

## ステップ5: Vertex AI Search のセットアップ

### 5.1 Vertex AI Search コンソールへアクセス

1. [Vertex AI Search Console](https://console.cloud.google.com/gen-app-builder/engines) にアクセス
2. 「検索アプリを作成」をクリック

### 5.2 検索エンジンの作成

1. **アプリタイプ**: 「検索」を選択
2. **コンテンツタイプ**:
   - 「構造化データ」または「非構造化データ」を選択
   - 行政事業レビューのPDFを扱う場合は「非構造化データ」を推奨
3. **会社名**: 任意の名前（例: "Government Reviews"）
4. **アプリ名**: `factcheck-search-app`
5. **リージョン**: `asia-northeast1` (東京)
6. 「続行」をクリック

### 5.3 データストアの作成

1. 「新しいデータストアを作成」を選択
2. **データソース**:
   - Cloud Storage を選択
   - 先ほど作成したバケットを指定
3. **データストア名**: `review-data-store`
4. 「作成」をクリック

### 5.4 データストアIDとエンジンIDを取得

データストアとサーチエンジンが作成されたら、それぞれのIDをメモします:

```bash
# データストアIDの確認方法
# GCPコンソールの Vertex AI Search > データストア から確認
# 形式: projects/PROJECT_NUMBER/locations/global/collections/default_collection/dataStores/DATA_STORE_ID

# サーチエンジンIDの確認方法
# GCPコンソールの Vertex AI Search > アプリ から確認
# 形式: projects/PROJECT_NUMBER/locations/global/collections/default_collection/engines/ENGINE_ID
```

## ステップ6: Secret Manager のセットアップ（フェーズ2用）

Twitter APIキーなどの機密情報を安全に管理するための設定です。

```bash
# シークレットの作成例（Twitter API Key用）
echo -n "YOUR_TWITTER_API_KEY" | gcloud secrets create twitter-api-key \
  --data-file=- \
  --replication-policy="automatic"

# シークレットへのアクセス権限を確認
gcloud secrets list
```

## ステップ7: 環境変数ファイルの設定

プロジェクトルートの `.env` ファイルに、取得した情報を記入します:

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集
# 以下の値を実際の値に置き換えてください
```

`.env` の設定例:

```env
# Google Cloud Platform
GCP_PROJECT_ID=factcheck-bot-dev-123456
GCP_LOCATION=asia-northeast1

# Vertex AI Search
VERTEX_AI_SEARCH_DATASTORE_ID=projects/123456789/locations/global/collections/default_collection/dataStores/review-data-store_1234567890
VERTEX_AI_SEARCH_ENGINE_ID=projects/123456789/locations/global/collections/default_collection/engines/factcheck-search-app_1234567890

# Cloud Storage
GCS_BUCKET_NAME=factcheck-bot-data-your-unique-id
GCS_DATA_PATH=data/review-data

# Application Settings
LOG_LEVEL=INFO
```

## ステップ8: IAM権限の設定

### 8.1 サービスアカウントの作成（Cloud Run用）

```bash
# サービスアカウントを作成
gcloud iam service-accounts create factcheck-bot-sa \
  --display-name="Factcheck Bot Service Account"

# 必要な権限を付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:factcheck-bot-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:factcheck-bot-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:factcheck-bot-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## ステップ9: 動作確認

### 9.1 認証の確認

```bash
# 認証情報の確認
gcloud auth list

# プロジェクト設定の確認
gcloud config list
```

### 9.2 APIアクセスのテスト

```bash
# Vertex AI APIが有効か確認
gcloud services list --enabled | grep aiplatform

# Cloud Storageへのアクセステスト
gcloud storage ls gs://${BUCKET_NAME}
```

## トラブルシューティング

### エラー: "API not enabled"

```bash
# 必要なAPIを再度有効化
gcloud services enable aiplatform.googleapis.com
```

### エラー: "Permission denied"

```bash
# 認証情報を再設定
gcloud auth application-default login
```

### バケット名の衝突

バケット名はグローバルで一意である必要があります。別の名前を試してください。

## チェックリスト

セットアップ完了前に、以下を確認してください:

- [ ] GCPプロジェクトが作成されている
- [ ] 必要なAPIが有効化されている
- [ ] gcloud CLIが設定されている
- [ ] アプリケーションデフォルト認証が完了している
- [ ] Cloud Storageバケットが作成されている
- [ ] Vertex AI Searchのデータストアとエンジンが作成されている
- [ ] `.env` ファイルに必要な情報が記入されている
- [ ] サービスアカウントが作成され、適切な権限が付与されている

## 次のステップ

GCP環境のセットアップが完了したら、以下のステップに進みます:

1. 行政事業レビューデータの収集
2. データのCloud Storageへのアップロード
3. Vertex AI Searchへのデータインポート
4. ファクトチェック機能の実装（F-01, F-03）

詳細は [README.md](../README.md) を参照してください。

## 参考リンク

- [Google Cloud Console](https://console.cloud.google.com/)
- [Vertex AI Search ドキュメント](https://cloud.google.com/generative-ai-app-builder/docs)
- [gcloud CLI リファレンス](https://cloud.google.com/sdk/gcloud/reference)
- [Secret Manager ドキュメント](https://cloud.google.com/secret-manager/docs)

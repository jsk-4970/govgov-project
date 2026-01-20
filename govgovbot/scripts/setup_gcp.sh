#!/bin/bash

# GCPセットアップスクリプト
# プロジェクトID: govgov-473916
#
# 使い方:
#   chmod +x scripts/setup_gcp.sh
#   ./scripts/setup_gcp.sh
#
# 前提条件:
#   - gcloud CLI がインストールされていること
#   - Google アカウントでログイン済みであること

set -e  # エラーが発生したら即座に終了

PROJECT_ID="govgov-473916"
REGION="asia-northeast1"
BUCKET_NAME="govgov-473916-data"

echo "=========================================="
echo "GCPセットアップスクリプト"
echo "プロジェクトID: $PROJECT_ID"
echo "=========================================="
echo ""

# gcloud CLIの確認
if ! command -v gcloud &> /dev/null; then
    echo "❌ エラー: gcloud CLI がインストールされていません"
    echo ""
    echo "以下のコマンドでインストールしてください:"
    echo "  brew install --cask google-cloud-sdk"
    echo ""
    echo "または、手動セットアップガイドを参照してください:"
    echo "  docs/MANUAL_GCP_SETUP.md"
    exit 1
fi

echo "✓ gcloud CLI が見つかりました"
echo ""

# プロジェクトの設定
echo "ステップ1: プロジェクトを設定中..."
gcloud config set project $PROJECT_ID
echo "✓ プロジェクト設定完了: $PROJECT_ID"
echo ""

# リージョンの設定
echo "ステップ2: デフォルトリージョンを設定中..."
gcloud config set compute/region $REGION
gcloud config set compute/zone ${REGION}-a
echo "✓ リージョン設定完了: $REGION"
echo ""

# APIの有効化
echo "ステップ3: 必要なAPIを有効化中..."
echo "  - Vertex AI API"
gcloud services enable aiplatform.googleapis.com

echo "  - Cloud Storage API"
gcloud services enable storage.googleapis.com

echo "  - Secret Manager API"
gcloud services enable secretmanager.googleapis.com

echo "  - Discovery Engine API (Vertex AI Search)"
gcloud services enable discoveryengine.googleapis.com

echo "✓ API有効化完了"
echo ""

# Cloud Storageバケットの作成
echo "ステップ4: Cloud Storageバケットを作成中..."
if gcloud storage buckets describe gs://$BUCKET_NAME &> /dev/null; then
    echo "ℹ️  バケット $BUCKET_NAME は既に存在します"
else
    gcloud storage buckets create gs://$BUCKET_NAME \
        --location=$REGION \
        --uniform-bucket-level-access
    echo "✓ バケット作成完了: gs://$BUCKET_NAME"
fi
echo ""

# サービスアカウントの作成
echo "ステップ5: サービスアカウントを作成中..."
SA_NAME="factcheck-bot-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SA_EMAIL &> /dev/null; then
    echo "ℹ️  サービスアカウント $SA_NAME は既に存在します"
else
    gcloud iam service-accounts create $SA_NAME \
        --display-name="Factcheck Bot Service Account"
    echo "✓ サービスアカウント作成完了: $SA_EMAIL"
fi
echo ""

# サービスアカウントへの権限付与
echo "ステップ6: サービスアカウントに権限を付与中..."

echo "  - Vertex AI ユーザー"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/aiplatform.user" \
    --condition=None \
    > /dev/null

echo "  - ストレージ オブジェクト閲覧者"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectViewer" \
    --condition=None \
    > /dev/null

echo "  - Secret Manager シークレット アクセサー"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    > /dev/null

echo "✓ 権限付与完了"
echo ""

# 完了メッセージ
echo "=========================================="
echo "✅ GCPセットアップ完了！"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "1. Vertex AI Searchのセットアップ（手動）"
echo "   → https://console.cloud.google.com/gen-app-builder/engines?project=$PROJECT_ID"
echo ""
echo "2. データストアとエンジンのIDを .env ファイルに設定"
echo ""
echo "3. アプリケーションデフォルト認証を設定:"
echo "   gcloud auth application-default login"
echo ""
echo "詳細は以下のドキュメントを参照してください:"
echo "  - docs/MANUAL_GCP_SETUP.md"
echo "  - docs/GCP_SETUP.md"
echo ""

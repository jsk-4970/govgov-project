#!/bin/bash

# GovGov Bot - Cloud Run デプロイスクリプト

set -e

PROJECT_ID="govgov-473916"
REGION="asia-northeast1"
SERVICE_NAME="factcheck-bot"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 GovGov Bot を Cloud Run にデプロイします..."
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo ""

# 現在のディレクトリを確認
if [ ! -f "Dockerfile" ]; then
  echo "❌ エラー: このスクリプトは govgovbot/ ディレクトリから実行してください"
  exit 1
fi

# Docker イメージをビルド
echo "📦 Docker イメージをビルド中..."
docker build -t ${IMAGE_NAME} .

# Docker イメージを Google Container Registry にプッシュ
echo "☁️  イメージを Google Container Registry にプッシュ中..."
docker push ${IMAGE_NAME}

# Cloud Run にデプロイ
echo "🌐 Cloud Run にデプロイ中..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --project ${PROJECT_ID}

echo ""
echo "✅ デプロイが完了しました！"
echo ""
echo "デプロイされたURL:"
gcloud run services describe ${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)'

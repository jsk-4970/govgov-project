#!/bin/bash

# GovGovWeb - Cloud Run デプロイスクリプト

set -e

PROJECT_ID="govgov-473916"
REGION="asia-northeast1"
SERVICE_NAME="govgovweb"
BACKEND_SERVICE_NAME="factcheck-bot"

echo "🚀 GovGovWeb を Cloud Run にデプロイします..."
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo ""

# Backend API（factcheck-bot）のURLを取得
echo "🔎 バックエンド (Cloud Run: ${BACKEND_SERVICE_NAME}) のURLを取得しています..."
BACKEND_API_URL=$(gcloud run services describe "${BACKEND_SERVICE_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format 'value(status.url)')

if [ -z "${BACKEND_API_URL}" ]; then
  echo "❌ エラー: ${BACKEND_SERVICE_NAME} のURLを取得できませんでした"
  exit 1
fi

echo "✅ バックエンド URL: ${BACKEND_API_URL}"
echo ""

# 現在のディレクトリを確認
if [ ! -f "package.json" ]; then
  echo "❌ エラー: このスクリプトは webapp/ ディレクトリから実行してください"
  exit 1
fi

# Cloud Run にデプロイ
echo "🌐 Cloud Run にデプロイ中..."
gcloud run deploy ${SERVICE_NAME} \
  --source . \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --set-env-vars BACKEND_API_URL=${BACKEND_API_URL} \
  --port 3000 \
  --memory 512Mi \
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

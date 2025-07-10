#!/bin/bash
# Google Cloud APIs有効化スクリプト

set -e

PROJECT_ID=$(gcloud config get-value project)
echo "🚀 プロジェクト $PROJECT_ID で必要なAPIを有効化します..."

# 必要なAPI一覧
APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "secretmanager.googleapis.com"
    "iamcredentials.googleapis.com"
    "sts.googleapis.com"
    "cloudresourcemanager.googleapis.com"
)

echo "📊 APIを有効化中..."
for api in "${APIS[@]}"; do
    echo "   - $api を有効化中..."
    gcloud services enable $api --project=$PROJECT_ID --quiet
done

echo ""
echo "✅ 全てのAPIが有効化されました！"
echo ""
echo "🔍 有効化されたAPIの確認:"
for api in "${APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo "   ✅ $api"
    else
        echo "   ❌ $api (再試行が必要な場合があります)"
    fi
done

echo ""
echo "🎯 次のステップ: Workload Identity Federation のセットアップ"
echo "   ./setup-github-actions-workload-identity.sh を実行してください"
#!/bin/bash
# 最小限の手動デプロイスクリプト

set -e

echo "🚀 最小限のCloud Runデプロイテストを開始..."

# プロジェクト設定確認
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Google Cloud プロジェクトが設定されていません"
    echo "gcloud config set project YOUR_PROJECT_ID を実行してください"
    exit 1
fi

echo "プロジェクト: $PROJECT_ID"

# 変数設定
SERVICE_NAME="slack-ai-bot-test"
REGION="asia-northeast1"
IMAGE_TAG="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/slack-ai-bot/${SERVICE_NAME}:$(date +%s)"

echo "サービス名: $SERVICE_NAME"
echo "イメージタグ: $IMAGE_TAG"

# Docker認証
echo "🔐 Docker認証中..."
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# 最小限のDockerイメージをビルド
echo "🐳 最小限のDockerイメージをビルド中..."
gcloud builds submit --config=cloudbuild-simple.yaml --substitutions=_IMAGE_TAG=$IMAGE_TAG --timeout=600s .

# Cloud Runにデプロイ
echo "🚀 Cloud Runにデプロイ中..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_TAG \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --timeout=300s \
    --memory=512Mi \
    --cpu=1000m \
    --max-instances=2 \
    --min-instances=0 \
    --port=8080 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID"

# サービスURLを取得
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo "✅ デプロイ完了！"
echo "サービスURL: $SERVICE_URL"

# サービス作成後、すでにトラフィックは100%のため設定不要
echo "✅ サービスが作成されました（トラフィック100%で自動設定）"

# ヘルスチェック
echo "🏥 ヘルスチェック実行中..."
sleep 30

echo "📡 接続テスト中..."
for i in {1..5}; do
    echo "テスト $i/5..."
    if curl -f -s "$SERVICE_URL/health" > /dev/null; then
        echo "✅ ヘルスチェック成功！"
        echo "レスポンス:"
        curl -s "$SERVICE_URL/health" | python -m json.tool
        echo ""
        echo "🧪 デバッグ情報:"
        curl -s "$SERVICE_URL/debug" | python -m json.tool
        break
    else
        echo "❌ ヘルスチェック失敗 (試行 $i/5)"
        if [ $i -eq 5 ]; then
            echo "🔍 エラーログを確認してください："
            echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION"
        else
            sleep 10
        fi
    fi
done

echo ""
echo "🎯 テスト完了！"
echo "   サービス名: $SERVICE_NAME"
echo "   URL: $SERVICE_URL"
echo "   ログ: gcloud run services logs read $SERVICE_NAME --region=$REGION"
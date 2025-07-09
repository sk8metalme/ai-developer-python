#!/bin/bash
# Google Cloud Run デプロイスクリプト

# 設定
SERVICE_NAME="slack-ai-bot"
REGION="asia-northeast1"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
IMAGE_NAME="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/slack-ai-bot/${SERVICE_NAME}"
TIMEOUT="540s"
MEMORY="1Gi"
MAX_INSTANCES="10"
MIN_INSTANCES="0"

echo "🚀 Google Cloud Run デプロイを開始します..."
echo "Service Name: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "Project ID: ${PROJECT_ID}"
echo "Image: ${IMAGE_NAME}"

# 必要な権限を確認
echo "📋 必要な権限を確認中..."
gcloud auth list --filter=status:ACTIVE --format="value(account)"

# Cloud Run API を有効化
echo "🔧 Cloud Run API を有効化中..."
gcloud services enable run.googleapis.com --project=${PROJECT_ID}
gcloud services enable cloudbuild.googleapis.com --project=${PROJECT_ID}
gcloud services enable artifactregistry.googleapis.com --project=${PROJECT_ID}

# Secret Manager にシークレットが存在するか確認
echo "🔐 Secret Manager のシークレットを確認中..."
required_secrets=(
    "SLACK_BOT_TOKEN"
    "SLACK_APP_TOKEN"
    "ANTHROPIC_API_KEY"
    "GITHUB_ACCESS_TOKEN"
    "CONFLUENCE_URL"
    "CONFLUENCE_USERNAME"
    "CONFLUENCE_API_TOKEN"
)

for secret in "${required_secrets[@]}"; do
    if ! gcloud secrets describe "${secret}" --project=${PROJECT_ID} &>/dev/null; then
        echo "⚠️  シークレット ${secret} が見つかりません"
        echo "以下のコマンドで作成してください:"
        echo "gcloud secrets create ${secret} --project=${PROJECT_ID}"
        echo "echo 'your_secret_value' | gcloud secrets versions add ${secret} --data-file=- --project=${PROJECT_ID}"
    else
        echo "✅ シークレット ${secret} が存在します"
    fi
done

# オプションのシークレット
optional_secrets=("ATLASSIAN_MCP_API_KEY")
for secret in "${optional_secrets[@]}"; do
    if gcloud secrets describe "${secret}" --project=${PROJECT_ID} &>/dev/null; then
        echo "✅ オプションのシークレット ${secret} が存在します"
    else
        echo "ℹ️  オプションのシークレット ${secret} は設定されていません"
    fi
done

# Docker イメージをビルド
echo "🐳 Docker イメージをビルド中..."
gcloud builds submit --tag=${IMAGE_NAME} --project=${PROJECT_ID} .

if [ $? -ne 0 ]; then
    echo "❌ Docker ビルドに失敗しました"
    exit 1
fi

# Cloud Run サービスをデプロイ
echo "🚀 Cloud Run サービスをデプロイ中..."
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --platform=managed \
    --allow-unauthenticated \
    --timeout=${TIMEOUT} \
    --memory=${MEMORY} \
    --max-instances=${MAX_INSTANCES} \
    --min-instances=${MIN_INSTANCES} \
    --port=8080 \
    --set-env-vars="CONFLUENCE_SPACE_KEY=DEV,LOG_LEVEL=INFO,GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --update-secrets="SLACK_BOT_TOKEN=SLACK_BOT_TOKEN:latest,SLACK_APP_TOKEN=SLACK_APP_TOKEN:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,GITHUB_ACCESS_TOKEN=GITHUB_ACCESS_TOKEN:latest,CONFLUENCE_URL=CONFLUENCE_URL:latest,CONFLUENCE_USERNAME=CONFLUENCE_USERNAME:latest,CONFLUENCE_API_TOKEN=CONFLUENCE_API_TOKEN:latest" \
    --verbosity=info

if [ $? -eq 0 ]; then
    echo "✅ デプロイが完了しました！"
    
    # サービスの URL を取得
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --format="value(status.url)")
    
    echo "🌐 Service URL: ${SERVICE_URL}"
    echo "📝 Slack アプリの設定で以下のURLを Webhook URL に設定してください:"
    echo "   ${SERVICE_URL}/slack/commands"
    
    # ヘルスチェック
    echo "🏥 ヘルスチェックを実行中..."
    curl -s "${SERVICE_URL}/health" || echo "ヘルスチェックに失敗しました"
    
else
    echo "❌ デプロイに失敗しました"
    exit 1
fi

echo "🎉 デプロイプロセスが完了しました！"
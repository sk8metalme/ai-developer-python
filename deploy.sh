#!/bin/bash
# Google Cloud Functions デプロイスクリプト

# 設定
FUNCTION_NAME="slack-ai-bot"
REGION="asia-northeast1"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
RUNTIME="python313"
TIMEOUT="540s"
MEMORY="1Gi"
MAX_INSTANCES="10"
MIN_INSTANCES="0"

echo "🚀 Google Cloud Functions デプロイを開始します..."
echo "Function Name: ${FUNCTION_NAME}"
echo "Region: ${REGION}"
echo "Project ID: ${PROJECT_ID}"

# 必要な権限を確認
echo "📋 必要な権限を確認中..."
gcloud auth list --filter=status:ACTIVE --format="value(account)"

# Cloud Functions API を有効化
echo "🔧 Cloud Functions API を有効化中..."
gcloud services enable cloudfunctions.googleapis.com --project=${PROJECT_ID}
gcloud services enable cloudbuild.googleapis.com --project=${PROJECT_ID}

# Secret Manager にシークレットが存在するか確認
echo "🔐 Secret Manager のシークレットを確認中..."
required_secrets=(
    "SLACK_BOT_TOKEN"
    "SLACK_SIGNING_SECRET"
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

# Cloud Functions をデプロイ
echo "🚀 Cloud Functions をデプロイ中..."
gcloud functions deploy ${FUNCTION_NAME} \
    --gen2 \
    --source=. \
    --entry-point=slack_bot \
    --runtime=${RUNTIME} \
    --trigger=http \
    --allow-unauthenticated \
    --timeout=${TIMEOUT} \
    --memory=${MEMORY} \
    --max-instances=${MAX_INSTANCES} \
    --min-instances=${MIN_INSTANCES} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --set-env-vars="CONFLUENCE_SPACE_KEY=DEV,LOG_LEVEL=INFO,GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-secrets="SLACK_BOT_TOKEN=SLACK_BOT_TOKEN:latest,SLACK_SIGNING_SECRET=SLACK_SIGNING_SECRET:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,GITHUB_ACCESS_TOKEN=GITHUB_ACCESS_TOKEN:latest,CONFLUENCE_URL=CONFLUENCE_URL:latest,CONFLUENCE_USERNAME=CONFLUENCE_USERNAME:latest,CONFLUENCE_API_TOKEN=CONFLUENCE_API_TOKEN:latest" \
    --verbosity=info

if [ $? -eq 0 ]; then
    echo "✅ デプロイが完了しました！"
    
    # 関数の URL を取得
    FUNCTION_URL=$(gcloud functions describe ${FUNCTION_NAME} --gen2 --region=${REGION} --project=${PROJECT_ID} --format="value(serviceConfig.uri)")
    
    echo "🌐 Function URL: ${FUNCTION_URL}"
    echo "📝 Slack アプリの設定で以下のURLを Webhook URL に設定してください:"
    echo "   ${FUNCTION_URL}"
    
    # ヘルスチェック
    echo "🏥 ヘルスチェックを実行中..."
    curl -s "${FUNCTION_URL}/health" || echo "ヘルスチェックに失敗しました"
    
else
    echo "❌ デプロイに失敗しました"
    exit 1
fi

echo "🎉 デプロイプロセスが完了しました！"
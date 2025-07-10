#!/bin/bash
# Secret Manager シークレット作成スクリプト

set -e

PROJECT_ID=$(gcloud config get-value project)
echo "🔐 プロジェクト $PROJECT_ID でSecret Managerシークレットを作成します..."

# 必要なシークレット一覧
SECRETS=(
    "SLACK_BOT_TOKEN"
    "SLACK_APP_TOKEN"
    "ANTHROPIC_API_KEY"
    "GITHUB_ACCESS_TOKEN"
    "CONFLUENCE_URL"
    "CONFLUENCE_USERNAME"
    "CONFLUENCE_API_TOKEN"
)

echo ""
echo "📝 以下のシークレットを作成します："
for secret in "${SECRETS[@]}"; do
    echo "   - $secret"
done

echo ""
echo "🔍 既存のシークレットを確認中..."

for secret in "${SECRETS[@]}"; do
    if gcloud secrets describe $secret --project=$PROJECT_ID &>/dev/null; then
        echo "   ✅ $secret は既に存在します"
    else
        echo "   📝 $secret を作成中..."
        gcloud secrets create $secret --project=$PROJECT_ID
        echo "   ✅ $secret を作成しました"
    fi
done

echo ""
echo "⚠️  次に各シークレットに値を設定してください："
echo ""

for secret in "${SECRETS[@]}"; do
    case $secret in
        "SLACK_BOT_TOKEN")
            echo "# Slack Bot User OAuth Token (xoxb- で始まる)"
            echo "echo 'YOUR_SLACK_BOT_TOKEN' | gcloud secrets versions add $secret --data-file=-"
            ;;
        "SLACK_APP_TOKEN")
            echo "# Slack App-Level Token (xapp- で始まる)"
            echo "echo 'YOUR_SLACK_APP_TOKEN' | gcloud secrets versions add $secret --data-file=-"
            ;;
        "ANTHROPIC_API_KEY")
            echo "# Anthropic Claude API Key (sk-ant- で始まる)"
            echo "echo 'YOUR_ANTHROPIC_API_KEY' | gcloud secrets versions add $secret --data-file=-"
            ;;
        "GITHUB_ACCESS_TOKEN")
            echo "# GitHub Personal Access Token (ghp_ で始まる)"
            echo "echo 'YOUR_GITHUB_ACCESS_TOKEN' | gcloud secrets versions add $secret --data-file=-"
            ;;
        "CONFLUENCE_URL")
            echo "# Confluence URL (https://your-domain.atlassian.net/wiki)"
            echo "echo 'YOUR_CONFLUENCE_URL' | gcloud secrets versions add $secret --data-file=-"
            ;;
        "CONFLUENCE_USERNAME")
            echo "# Confluence Username (メールアドレス)"
            echo "echo 'YOUR_CONFLUENCE_USERNAME' | gcloud secrets versions add $secret --data-file=-"
            ;;
        "CONFLUENCE_API_TOKEN")
            echo "# Confluence API Token"
            echo "echo 'YOUR_CONFLUENCE_API_TOKEN' | gcloud secrets versions add $secret --data-file=-"
            ;;
    esac
    echo ""
done

echo "🎯 設定完了後の次のステップ:"
echo "   1. GitHub リポジトリでWIF_PROVIDERとWIF_SERVICE_ACCOUNTのSecretsを設定"
echo "   2. main.py を修正してmainブランチにマージ"
echo "   3. GitHub Actionsによる自動デプロイのテスト"
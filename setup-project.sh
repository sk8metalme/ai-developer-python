#!/bin/bash
# プロジェクト設定スクリプト
# このファイルは .gitignore で管理対象外です

set -e

echo "🚀 AI Developer Bot プロジェクト設定"
echo ""

# 現在のgcloudプロジェクトを確認
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")

if [ -n "$CURRENT_PROJECT" ]; then
    echo "現在のgcloudプロジェクト: $CURRENT_PROJECT"
    read -p "このプロジェクトを使用しますか？ [Y/n]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        read -p "使用するプロジェクトIDを入力してください: " PROJECT_ID
        gcloud config set project "$PROJECT_ID"
    else
        PROJECT_ID="$CURRENT_PROJECT"
    fi
else
    read -p "Google Cloud プロジェクトIDを入力してください: " PROJECT_ID
    gcloud config set project "$PROJECT_ID"
fi

# 環境変数ファイルを作成
cat > .env.local << EOF
# Google Cloud 設定
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_REGION=asia-northeast1

# このファイルは .gitignore で管理対象外です
# 本番環境では Secret Manager を使用してください
EOF

echo ""
echo "✅ プロジェクト設定完了"
echo "   プロジェクトID: $PROJECT_ID"
echo "   設定ファイル: .env.local (Git管理対象外)"
echo ""
echo "次のステップ:"
echo "1. Secret Manager にトークンを設定"
echo "2. ./deploy.sh でデプロイ実行"
echo ""
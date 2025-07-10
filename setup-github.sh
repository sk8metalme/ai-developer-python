#!/bin/bash
# GitHub Secrets設定ガイドスクリプト

echo "🔑 GitHub Secrets の設定手順"
echo "================================"
echo ""

echo "📍 設定場所:"
echo "   https://github.com/sk8metalme/ai-developer-python/settings/secrets/actions"
echo ""

echo "🔐 設定する2つのSecrets:"
echo ""

echo "1️⃣  WIF_PROVIDER"
echo "   Name: WIF_PROVIDER"
echo "   Value: projects/224087487695/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider"
echo ""

echo "2️⃣  WIF_SERVICE_ACCOUNT"
echo "   Name: WIF_SERVICE_ACCOUNT"
echo "   Value: github-actions-deploy@ai-developer-465404.iam.gserviceaccount.com"
echo ""

echo "📋 設定手順:"
echo "   1. 上記URLにアクセス"
echo "   2. 'New repository secret' ボタンをクリック"
echo "   3. Name と Value を入力"
echo "   4. 'Add secret' ボタンをクリック"
echo "   5. 2つ目のSecretも同様に追加"
echo ""

echo "✅ 設定完了の確認:"
echo "   Secrets一覧に以下が表示されればOK:"
echo "   ✅ WIF_PROVIDER"
echo "   ✅ WIF_SERVICE_ACCOUNT"
echo ""

echo "🚀 次のステップ:"
echo "   GitHub Secrets設定完了後、mainブランチにマージしてデプロイテスト"

# GitHub CLI がインストールされている場合は、リポジトリを開く
if command -v gh &> /dev/null; then
    echo ""
    echo "💡 GitHub CLIが利用可能です。以下のコマンドでSecretsページを開けます:"
    echo "   gh repo view sk8metalme/ai-developer-python --web"
    echo "   その後、Settings > Secrets and variables > Actions に移動"
fi
# 🚀 GitHub Actions → Google Cloud Run デプロイ設定ガイド

このガイドでは、GitHub Actionsを使用してGoogle Cloud Runに自動デプロイする環境を構築します。

## 📋 前提条件

- Google Cloudプロジェクトの作成済み
- Google Cloud SDKのインストール済み
- GitHub リポジトリの準備済み
- 必要なトークン・APIキーの準備済み

## 🔧 セットアップ手順

### Step 1: Google Cloud認証

```bash
# Google Cloudにログイン
gcloud auth login

# プロジェクトの設定確認
gcloud config list
```

### Step 2: 必要なAPIの有効化

```bash
# APIを有効化
./enable-apis.sh
```

### Step 3: Workload Identity Federation の設定

```bash
# WIF設定スクリプトを実行
./setup-github-actions-workload-identity.sh
```

このスクリプトは以下を設定します：
- Workload Identity Pool の作成
- OIDC Provider の作成
- サービスアカウントの作成と権限付与
- GitHub Actions用の認証設定

### Step 4: Secret Manager シークレットの作成

```bash
# シークレットを作成
./setup-sm.sh
```

### Step 5: シークレット値の設定

各シークレットに実際の値を設定します：

```bash
# Slack Bot Token (xoxb- で始まる)
echo 'xoxb-your-actual-token' | gcloud secrets versions add SLACK_BOT_TOKEN --data-file=-

# Slack App Token (xapp- で始まる)
echo 'xapp-your-actual-token' | gcloud secrets versions add SLACK_APP_TOKEN --data-file=-

# Anthropic API Key (sk-ant- で始まる)
echo 'sk-ant-your-actual-key' | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-

# GitHub Access Token (ghp_ で始まる)
echo 'ghp_your-actual-token' | gcloud secrets versions add GITHUB_ACCESS_TOKEN --data-file=-

# Confluence設定（オプション）
echo 'https://your-domain.atlassian.net/wiki' | gcloud secrets versions add CONFLUENCE_URL --data-file=-
echo 'your-email@example.com' | gcloud secrets versions add CONFLUENCE_USERNAME --data-file=-
echo 'your-confluence-api-token' | gcloud secrets versions add CONFLUENCE_API_TOKEN --data-file=-
```

### Step 6: GitHub Secrets の設定

`setup-github-actions-workload-identity.sh` の実行結果から、以下の値をコピーしてGitHubリポジトリのSecretsに設定：

1. GitHub リポジトリ → Settings → Secrets and variables → Actions
2. 以下のSecretsを追加：

```
Name: WIF_PROVIDER
Value: [スクリプトで出力されたWIF_PROVIDER値]

Name: WIF_SERVICE_ACCOUNT  
Value: [スクリプトで出力されたWIF_SERVICE_ACCOUNT値]
```

詳細は `GITHUB_SECRETS_SETUP.md` を参照してください。

## 🎯 デプロイテスト

### 自動デプロイのトリガー

1. **mainブランチへのpush** - 本番環境にデプロイ
2. **PRのマージ** - ステージング環境にデプロイ  
3. **手動実行** - Actions → Deploy to Cloud Run → Run workflow

### デプロイ確認

```bash
# デプロイされたサービスの確認
gcloud run services list --region=asia-northeast1

# サービスURLの確認
gcloud run services describe slack-ai-bot --region=asia-northeast1 --format="value(status.url)"

# ヘルスチェック
curl [SERVICE_URL]/health
```

## 📊 設定されるリソース

### Google Cloud Resources

- **Cloud Run サービス**: `slack-ai-bot` (本番) / `slack-ai-bot-staging` (ステージング)
- **Artifact Registry**: `slack-ai-bot` リポジトリ
- **Secret Manager**: アプリケーション用シークレット
- **IAM**: GitHub Actions用サービスアカウントと権限
- **Workload Identity Federation**: セキュアな認証

### GitHub Actions

- **deploy.yml**: Cloud Runデプロイワークフロー
- **test.yml**: テスト・リントワークフロー

## 🔍 トラブルシューティング

### よくある問題

1. **認証エラー**
   - `gcloud auth login` を再実行
   - プロジェクトIDが正しいか確認

2. **権限エラー**
   - IAMロールが正しく設定されているか確認
   - WIF設定スクリプトを再実行

3. **デプロイエラー**
   - GitHub Actionsログを確認
   - Secret Managerの値を確認

### 有用なコマンド

```bash
# ログの確認
gcloud run services logs read slack-ai-bot --region=asia-northeast1

# サービスの詳細確認
gcloud run services describe slack-ai-bot --region=asia-northeast1

# シークレットの確認
gcloud secrets list
gcloud secrets versions access latest --secret=SLACK_BOT_TOKEN

# ビルド履歴の確認
gcloud builds list --limit=10
```

## 📚 関連ドキュメント

- [README_GITHUB_ACTIONS.md](./README_GITHUB_ACTIONS.md) - GitHub Actions詳細設定
- [README_SOCKET_MODE.md](./README_SOCKET_MODE.md) - Slack Socket Mode設定
- [GITHUB_SECRETS_SETUP.md](./GITHUB_SECRETS_SETUP.md) - GitHub Secrets設定手順
- [CLAUDE.md](./CLAUDE.md) - プロジェクト概要とアーキテクチャ

## 🎉 完了！

設定完了後、Slackでコマンドをテストしてみてください：

```
/develop your-repo の main.py に Hello World機能を追加
/design-mcp my-app の ユーザー認証機能 について JWT認証を使用
/confluence-search API設計 in:DEV
```
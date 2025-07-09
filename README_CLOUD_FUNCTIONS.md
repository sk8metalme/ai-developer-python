# Google Cloud Functions デプロイガイド

このガイドでは、Slack AI開発ボットをGoogle Cloud Functionsにデプロイする方法を説明します。

## 前提条件

1. Google Cloud プロジェクトの作成
2. Google Cloud CLI (gcloud) のインストールと認証
3. 必要な権限の付与
4. Slack アプリの作成と設定

## 1. プロジェクトの準備

### Google Cloud プロジェクトの設定

```bash
# プロジェクトIDを設定
export GOOGLE_CLOUD_PROJECT="your-project-id"

# プロジェクトを設定
gcloud config set project $GOOGLE_CLOUD_PROJECT

# 必要なAPIを有効化
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

## 2. Secret Manager の設定

### 必要なシークレットの作成

```bash
# Slack 関連
gcloud secrets create SLACK_BOT_TOKEN
gcloud secrets create SLACK_SIGNING_SECRET

# Anthropic API
gcloud secrets create ANTHROPIC_API_KEY

# GitHub API
gcloud secrets create GITHUB_ACCESS_TOKEN

# Confluence 関連
gcloud secrets create CONFLUENCE_URL
gcloud secrets create CONFLUENCE_USERNAME
gcloud secrets create CONFLUENCE_API_TOKEN

# オプション: リモートMCP API
gcloud secrets create ATLASSIAN_MCP_API_KEY
```

### シークレットの値を設定

```bash
# 各シークレットに値を設定
echo "your-slack-bot-token" | gcloud secrets versions add SLACK_BOT_TOKEN --data-file=-
echo "your-slack-signing-secret" | gcloud secrets versions add SLACK_SIGNING_SECRET --data-file=-
echo "your-anthropic-api-key" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-
echo "your-github-access-token" | gcloud secrets versions add GITHUB_ACCESS_TOKEN --data-file=-
echo "https://your-company.atlassian.net/wiki" | gcloud secrets versions add CONFLUENCE_URL --data-file=-
echo "your-confluence-email" | gcloud secrets versions add CONFLUENCE_USERNAME --data-file=-
echo "your-confluence-api-token" | gcloud secrets versions add CONFLUENCE_API_TOKEN --data-file=-
```

## 3. デプロイメント

### 自動デプロイ

```bash
# デプロイスクリプトを実行
./deploy.sh
```

### 手動デプロイ

```bash
# 手動でデプロイする場合
gcloud functions deploy slack-ai-bot \
    --gen2 \
    --source=. \
    --entry-point=slack_bot \
    --runtime=python313 \
    --trigger=http \
    --allow-unauthenticated \
    --timeout=540s \
    --memory=1Gi \
    --max-instances=10 \
    --min-instances=0 \
    --region=asia-northeast1 \
    --set-env-vars="CONFLUENCE_SPACE_KEY=DEV,LOG_LEVEL=INFO" \
    --set-secrets="SLACK_BOT_TOKEN=SLACK_BOT_TOKEN:latest,SLACK_SIGNING_SECRET=SLACK_SIGNING_SECRET:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,GITHUB_ACCESS_TOKEN=GITHUB_ACCESS_TOKEN:latest,CONFLUENCE_URL=CONFLUENCE_URL:latest,CONFLUENCE_USERNAME=CONFLUENCE_USERNAME:latest,CONFLUENCE_API_TOKEN=CONFLUENCE_API_TOKEN:latest"
```

## 4. Slack アプリの設定

### Webhook URL の設定

デプロイ完了後、取得したFunction URLをSlack アプリの設定に追加します。

```
https://REGION-PROJECT_ID.cloudfunctions.net/slack-ai-bot
```

### 必要な権限

Slack アプリに以下の権限を付与してください：

- `commands` (スラッシュコマンド用)
- `chat:write` (メッセージ送信用)

### スラッシュコマンドの設定

以下のコマンドを Slack アプリに追加：

- `/develop` - 従来の開発機能
- `/design` - 設計ドキュメント作成（従来版）
- `/design-mcp` - 設計ドキュメント作成（MCP版）
- `/develop-from-design` - 設計ベース開発（従来版）
- `/develop-from-design-mcp` - 設計ベース開発（MCP版）
- `/confluence-search` - Confluence検索

## 5. 監視とトラブルシューティング

### ログの確認

```bash
# 関数のログを確認
gcloud functions logs read slack-ai-bot --region=asia-northeast1

# リアルタイムログの監視
gcloud functions logs tail slack-ai-bot --region=asia-northeast1
```

### ヘルスチェック

```bash
# 関数のヘルスチェック
curl https://REGION-PROJECT_ID.cloudfunctions.net/slack-ai-bot/health
```

### デバッグ

```bash
# 関数の詳細情報を表示
gcloud functions describe slack-ai-bot --gen2 --region=asia-northeast1

# 関数の設定を確認
gcloud functions describe slack-ai-bot --gen2 --region=asia-northeast1 --format="yaml"
```

## 6. スケーリングとパフォーマンス

### インスタンス数の調整

```bash
# インスタンス数を調整
gcloud functions deploy slack-ai-bot \
    --gen2 \
    --max-instances=20 \
    --min-instances=1 \
    --region=asia-northeast1
```

### メモリとタイムアウトの調整

```bash
# メモリとタイムアウトを調整
gcloud functions deploy slack-ai-bot \
    --gen2 \
    --memory=2Gi \
    --timeout=900s \
    --region=asia-northeast1
```

## 7. セキュリティ

### IAM 権限の最小化

```bash
# 関数用のサービスアカウントを作成
gcloud iam service-accounts create slack-ai-bot-sa \
    --description="Slack AI Bot Service Account" \
    --display-name="Slack AI Bot"

# 必要な権限のみを付与
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:slack-ai-bot-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### VPC コネクタの使用（オプション）

```bash
# VPC コネクタを作成
gcloud compute networks vpc-access connectors create slack-ai-bot-connector \
    --network default \
    --region asia-northeast1 \
    --range 10.8.0.0/28

# 関数でVPCコネクタを使用
gcloud functions deploy slack-ai-bot \
    --gen2 \
    --vpc-connector=slack-ai-bot-connector \
    --region=asia-northeast1
```

## 8. コスト最適化

### 適切なリソース設定

- **メモリ**: 1Gi（通常使用には十分）
- **タイムアウト**: 540s（9分）
- **最大インスタンス**: 10（トラフィックに応じて調整）
- **最小インスタンス**: 0（コスト削減）

### 監視とアラート

```bash
# Cloud Monitoring でアラートを設定
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

## トラブルシューティング

### よくある問題

1. **タイムアウト**: 長時間実行される処理がある場合、タイムアウト値を増やす
2. **メモリ不足**: メモリ使用量が多い場合、メモリ設定を増やす
3. **コールドスタート**: 最小インスタンスを1に設定してコールドスタートを減らす
4. **権限エラー**: Secret Manager やその他のサービスへの権限を確認

### ログの確認方法

```bash
# エラーログのみを表示
gcloud functions logs read slack-ai-bot --region=asia-northeast1 --filter="severity>=ERROR"

# 特定の時間範囲のログを表示
gcloud functions logs read slack-ai-bot --region=asia-northeast1 --filter="timestamp>=2023-01-01T00:00:00Z"
```

これで Google Cloud Functions での Slack AI開発ボットのデプロイが完了します。
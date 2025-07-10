# Slack Socket Mode 設定ガイド

このガイドでは、Slack AI開発ボットをSocket Modeで設定する方法を説明します。Socket Modeを使用することで、外部からのHTTPアクセスを必要とせず、Slackとの双方向WebSocket通信が可能になります。

## Socket Mode の利点

- 🔒 **セキュリティ**: 外部エンドポイントが不要
- 🚀 **簡単な設定**: HTTPサーバーの設定が不要
- 💾 **リアルタイム**: WebSocketによる双方向通信
- 🌐 **NAT/ファイアウォール対応**: 外部からのアクセス許可が不要

## 必要な環境変数

Socket Modeでは以下の環境変数が必要です：

```bash
SLACK_BOT_TOKEN      # Bot User OAuth Token
SLACK_APP_TOKEN      # App-Level Token (Socket Mode用)
ANTHROPIC_API_KEY    # Claude API Key
GITHUB_ACCESS_TOKEN  # GitHub Personal Access Token
```

## Slack アプリの設定

### 1. Socket Mode の有効化

1. https://api.slack.com/apps でアプリを選択
2. 左メニューから **"Socket Mode"** をクリック
3. **"Enable Socket Mode"** をオンにする
4. **"App-Level Token"** を作成：
   - Token Name: `slack-ai-bot-socket`
   - Scopes: `connections:write`
   - **"Generate"** をクリック
   - 生成されたトークンをコピー（`xapp-` で始まる）

### 2. OAuth & Permissions の設定

1. 左メニューから **"OAuth & Permissions"** をクリック
2. **"Bot Token Scopes"** に以下を追加：
   - `commands` (スラッシュコマンド用)
   - `chat:write` (メッセージ送信用)
   - `chat:write.public` (パブリックチャンネル投稿用)

### 3. Slash Commands の設定

Socket Modeでは、Slash Commandsの **Request URL は設定不要** です。

1. 左メニューから **"Slash Commands"** をクリック
2. 以下のコマンドを作成（Request URLは空欄でOK）：

#### `/develop`
- **Command**: `/develop`
- **Short Description**: `AI開発ボット - コード生成とPR作成`
- **Usage Hint**: `[owner/repo] の [file-path] に [instruction]`

#### `/design-mcp`
- **Command**: `/design-mcp`
- **Short Description**: `MCP版設計ドキュメント作成`
- **Usage Hint**: `[project] の [feature] について [requirements]`

#### `/develop-from-design-mcp`
- **Command**: `/develop-from-design-mcp`
- **Short Description**: `MCP版設計ベース開発`
- **Usage Hint**: `[confluence-url] の [file-path] に実装`

#### `/confluence-search`
- **Command**: `/confluence-search`
- **Short Description**: `Confluence検索`
- **Usage Hint**: `[query] [in:space-key]`

### 4. Event Subscriptions（オプション）

Socket Modeでは Event Subscriptions も自動処理されます。
特別な設定は不要ですが、必要に応じて有効化できます。

## Secret Manager の設定

### SLACK_APP_TOKEN の追加

```bash
# Secret を作成
gcloud secrets create SLACK_APP_TOKEN

# App-Level Token を設定（xapp- で始まるトークン）
echo "xapp-1-A1234567890-1234567890123-abcdef..." | gcloud secrets versions add SLACK_APP_TOKEN --data-file=-
```

### 既存のシークレット

以下のシークレットがすでに設定されている必要があります：

```bash
gcloud secrets list --filter="name:SLACK_BOT_TOKEN OR name:ANTHROPIC_API_KEY OR name:GITHUB_ACCESS_TOKEN"
```

## デプロイメント

### Cloud Run での実行

```bash
# デプロイスクリプトを実行
./deploy.sh
```

### ローカルでの実行

```bash
# 環境変数を設定
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GITHUB_ACCESS_TOKEN="ghp_..."

# 依存関係をインストール
pip install -r requirements.txt

# Socket Mode で起動
python main.py
```

## トークンの取得方法

### Bot User OAuth Token (`SLACK_BOT_TOKEN`)

1. **"OAuth & Permissions"** ページで取得
2. **"Bot User OAuth Token"** をコピー
3. `xoxb-` で始まるトークン

### App-Level Token (`SLACK_APP_TOKEN`)

1. **"Socket Mode"** ページで **"App-Level Token"** を作成
2. Scope: `connections:write`
3. `xapp-` で始まるトークン

## 動作確認

### 1. ログの確認

```bash
# Cloud Run ログ
gcloud run services logs read slack-ai-bot --region=asia-northeast1

# ローカル実行時
python main.py
```

期待されるログ出力：
```
🤖 Slack AI開発ボット (Socket Mode) を起動します...
Socket Mode で接続を開始します...
⚡️ Bolt app is running! (Socket Mode)
```

### 2. Slack でのテスト

```bash
# 基本的な開発コマンド
/develop sk8metalme/test-repo の main.py に Hello World機能を追加

# 設計ドキュメント作成
/design-mcp my-app の ユーザー認証機能 について JWT認証を使用

# Confluence検索
/confluence-search API設計 in:DEV
```

## トラブルシューティング

### よくある問題

1. **接続エラー**
   ```
   Failed to connect to Socket Mode
   ```
   - `SLACK_APP_TOKEN` が正しく設定されているか確認
   - Socket Modeが有効になっているか確認

2. **権限エラー**
   ```
   missing_scope: commands
   ```
   - Bot Token Scopes に `commands` が追加されているか確認

3. **環境変数エラー**
   ```
   必要な環境変数がすべて設定されていません
   ```
   - Secret Manager の値が正しく設定されているか確認

### デバッグ方法

```bash
# Secret Manager の確認
gcloud secrets list

# 特定のシークレットの確認
gcloud secrets versions access latest --secret="SLACK_APP_TOKEN"

# Cloud Run サービスの環境変数確認
gcloud run services describe slack-ai-bot --region=asia-northeast1 --format="value(spec.template.spec.containers[0].env[].name)"
```

## 従来のHTTP Modeとの違い

| 項目 | HTTP Mode | Socket Mode |
|------|-----------|-------------|
| **エンドポイント** | 必要（公開URL） | 不要 |
| **認証** | Signing Secret | App-Level Token |
| **通信方式** | HTTP POST | WebSocket |
| **セキュリティ** | 外部公開必要 | 内部接続のみ |
| **設定の複雑さ** | 高 | 低 |

Socket Modeを使用することで、よりシンプルで安全なSlackボットの運用が可能になります。
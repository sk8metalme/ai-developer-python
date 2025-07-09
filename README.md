# Slack AI開発ボット

Anthropic社のClaude APIを使用して、自動的にコード変更を生成し、GitHubリポジトリにプルリクエストを作成するSlackボットです。

## 機能

- 🤖 **AI駆動コード生成**: 自然言語指示に基づいてClaude APIでコードを生成
- 📱 **Slack連携**: 複数のスラッシュコマンドに対応（`/develop`, `/design`, `/design-mcp`, `/develop-from-design`, `/develop-from-design-mcp`, `/confluence-search`）
- 🔗 **GitHub連携**: ブランチ、コミット、プルリクエストを自動作成
- 📋 **設計ドキュメント作成**: 要件からConfluenceに詳細設計書を自動生成
- 🏗️ **設計ベース開発**: Confluenceの設計書からコードを生成
- 🎯 **MCP統合**: sooperset/mcp-atlassianのDockerイメージを使用したConfluence連携（フォールバック機能付き）
- ⚡ **非同期処理**: Slackレスポンスをブロックしない長時間実行タスクの処理
- 🛡️ **セキュリティ**: リクエスト署名検証と適切なOAuthスコープ

## クイックスタート

### 1. 前提条件

- Python 3.8+
- 管理者権限のあるSlackワークスペース
- リポジトリアクセス権限のあるGitHubアカウント
- Anthropic APIキー
- Confluenceアカウント（設計機能を使用する場合）
- Docker環境（MCP機能を使用する場合）

### 2. インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-username/ai-developer-python.git
cd ai-developer-python

# 依存関係をインストール
pip install -r requirements.txt
```

### 3. 設定

1. **基本環境変数を`setup-env.sh`で設定**:
   ```bash
   export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
   export SLACK_SIGNING_SECRET="your-slack-signing-secret"
   export ANTHROPIC_API_KEY="sk-ant-your-anthropic-api-key"
   export GITHUB_ACCESS_TOKEN="ghp_your-github-token"
   
   # Confluence連携（オプショナル）
   export CONFLUENCE_URL="https://your-company.atlassian.net/wiki"
   export CONFLUENCE_USERNAME="your-email@company.com"
   export CONFLUENCE_API_TOKEN="your-confluence-api-token"
   export CONFLUENCE_SPACE_KEY="DEV"
   ```

2. **環境変数を読み込み**:
   ```bash
   source setup-env.sh
   ```

### 4. Slackアプリの設定

1. https://api.slack.com/apps で新しいSlackアプリを作成
2. **OAuthスコープ**を追加:
   - `commands`（スラッシュコマンド用）
3. **スラッシュコマンド**を作成:
   - コマンド: `/develop`
   - リクエストURL: `https://your-server.com/slack/commands`
4. **Bot User OAuth Token**と**Signing Secret**を取得

### 5. GitHub設定

1. https://github.com/settings/tokens でGitHub Personal Access Tokenを作成
2. 以下のスコープを付与:
   - `repo`（完全なリポジトリアクセス）

### 6. ボットの実行

```bash
python aibot.py
```

ボットはポート3000で起動します（`PORT`環境変数で設定可能）。

## 使用方法

### 従来の開発機能

Slackで以下の形式で`/develop`コマンドを使用してください：

```
/develop [オーナー/リポジトリ] の [ファイルパス] に [指示]
```

**使用例:**
```
/develop sk8metalme/test-repo の main.py に HelloWorldを出力する機能を追加
```

### 新機能: 設計ドキュメント作成

要件から詳細な設計ドキュメントを自動生成してConfluenceに作成：

#### 従来版
```
/design [プロジェクト名] の [機能名] について [要件・制約]
```

#### MCP版（推奨）
```
/design-mcp [プロジェクト名] の [機能名] について [要件・制約]
```

**使用例:**
```
/design-mcp my-app の ユーザー認証機能 について JWT認証を使用し、ログイン・ログアウト・パスワードリセット機能を含む
```

### 新機能: 設計ベース開発

Confluenceの設計ドキュメントからコードを生成：

#### 従来版
```
/develop-from-design [confluence-url] の [ファイルパス] に実装
```

#### MCP版（推奨）
```
/develop-from-design-mcp [confluence-url] の [ファイルパス] に実装
```

**使用例:**
```
/develop-from-design-mcp https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装
```

### 新機能: Confluence検索

Confluenceページを検索：

```
/confluence-search [検索クエリ] [in:スペースキー]
```

**使用例:**
```
/confluence-search ユーザー認証 in:DEV
```

## 動作の仕組み

### 従来の開発フロー
1. **コマンド処理**: ボットがSlackからスラッシュコマンドを受信
2. **リポジトリアクセス**: 指定されたGitHubリポジトリから現在のコードを取得
3. **AI生成**: コードと指示をClaude APIに送信して修正
4. **ブランチ作成**: 生成された変更内容で新しいブランチを作成
5. **プルリクエスト**: 修正されたコードでPRを作成
6. **通知**: SlackでPR URLを応答

### 設計ドキュメント作成フロー
1. **要件受信**: Slackで`/design`または`/design-mcp`コマンドを受信
2. **設計生成**: Claude APIで詳細な設計ドキュメントを生成
3. **Confluence作成**: 設計書をConfluenceページとして作成（MCP版では直接API呼び出しにフォールバック）
4. **通知**: Slackで設計書URLを応答

### 設計ベース開発フロー
1. **設計取得**: Confluenceから設計ドキュメントを取得（MCP版では直接API呼び出しにフォールバック）
2. **コード生成**: 設計内容に基づいてClaude APIでコードを生成
3. **コード提供**: 生成されたコードをSlackで応答

## アーキテクチャ

- **aibot.py**: メインアプリケーションファイル
- **atlassian_mcp_integration.py**: MCP連携モジュール（フォールバック機能付き）
- **Flaskサーバー**: SlackからのHTTPリクエストを処理
- **スレッド処理**: 長時間実行タスクの非同期処理
- **エラーハンドリング**: 包括的なログ記録とエラー回復
- **sooperset/mcp-atlassian**: Confluence連携用Dockerイメージ

## 依存関係

- `slack-bolt`: Slackアプリフレームワーク
- `anthropic`: Claude APIクライアント
- `PyGithub`: GitHub APIラッパー
- `flask`: Webフレームワーク
- `requests`: HTTPライブラリ
- `atlassian-python-api`: Confluence API操作
- `beautifulsoup4`: HTML解析
- `markdown`: マークダウン生成

## トラブルシューティング

### よくある問題

1. **「Not Found」GitHubエラー**
   - リポジトリが存在しアクセス可能であることを確認
   - GitHubトークンの権限を確認

2. **「Illegal header value」エラー**
   - APIキーから末尾の改行文字を削除
   - 環境変数が正しく設定されていることを確認

3. **Slack権限エラー**
   - ボットが`commands` OAuthスコープを持っていることを確認
   - 署名シークレットが正しいことを確認

4. **リクエスト署名検証失敗**
   - `SLACK_SIGNING_SECRET`がSlackアプリと一致することを確認
   - 環境変数に末尾の空白文字がないことを確認

### デバッグモード

詳細なログ記録のため、ボットには包括的なデバッグ情報が含まれています：
- HTTPリクエスト/レスポンスの詳細
- API呼び出しトレース
- コンテキスト付きエラースタックトレース

## 貢献

1. リポジトリをフォーク
2. 機能ブランチを作成
3. 変更を実施
4. 該当する場合はテストを追加
5. プルリクエストを提出

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています。

## セキュリティ

- シークレットをリポジトリにコミットしない
- すべての機密データに環境変数を使用
- APIキーとトークンを定期的にローテーション
- リクエスト署名検証を有効化
# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリのコードを扱う際のガイダンスを提供します。

## プロジェクト概要

これは、GitHubとAnthropic社のClaude APIと連携するSlack AI開発ボットです。ボットはSlackからのスラッシュコマンドを受け取り、自動的にコード変更を生成し、GitHubリポジトリにプルリクエストを作成します。

## アーキテクチャ

アプリケーションは以下のコンポーネントで構成されています：

- **Slack連携**: Slack BoltフレームワークとFlaskアダプターを使用して複数のスラッシュコマンドを処理（`/develop`, `/design`, `/design-mcp`, `/develop-from-design`, `/develop-from-design-mcp`, `/confluence-search`）
- **GitHub連携**: PyGithubライブラリを使用したリポジトリ操作（ファイル読み取り、ブランチ作成、PR作成）
- **AI連携**: 自然言語指示に基づくコード生成のためのAnthropic Claude API
- **Confluence連携**: 
  - **MCP版**: Atlassian公式Remote MCP Server（`https://mcp.atlassian.com/v1/sse`）を使用した簡素化実装
  - **Direct API版**: atlassian-python-api を使用した直接API呼び出しによるフォールバック実装
- **非同期処理**: Slackの3秒タイムアウトをブロックしない長時間実行タスクの処理
- **HTTPサーバー**: Slack webhookリクエストを受信するFlaskベースのHTTPサーバー

## 主要コンポーネント

### aibot.py（メインアプリケーション）
- `get_repo_content()`: GitHubリポジトリからファイル内容を取得
- `create_github_pr()`: 新しいブランチを作成し、ファイルを更新し、プルリクエストを作成
- `process_development_task()`: ワークフロー全体を統制するメインの非同期タスクハンドラー
- `handle_develop_command()`: 即座に応答するSlackコマンドハンドラー
- `handle_design_command()`: 設計ドキュメント作成コマンドハンドラー
- `handle_develop_from_design_command()`: 設計ベース開発コマンドハンドラー
- `handle_design_mcp_command()`: MCP版設計ドキュメント作成コマンドハンドラー
- `handle_develop_from_design_mcp_command()`: MCP版設計ベース開発コマンドハンドラー
- `handle_confluence_search_command()`: Confluence検索コマンドハンドラー

### atlassian_mcp_integration.py（MCP連携）
- `AtlassianMCPClient`: Atlassian MCP Serverとの連携クライアント
- `create_confluence_page_mcp()`: MCP経由でConfluenceページを作成
- `get_confluence_page_mcp()`: MCP経由でConfluenceページ内容を取得
- `search_confluence_pages_mcp()`: MCP経由でConfluenceページを検索
- `generate_design_document_mcp()`: MCP対応版設計ドキュメント生成

## 環境設定

### 基本環境変数（必須）

アプリケーションには4つの基本環境変数が必要です：
- `SLACK_BOT_TOKEN`: Slackボット認証トークン（`commands`スコープが必要）
- `SLACK_SIGNING_SECRET`: リクエスト検証用のSlackアプリ署名シークレット
- `ANTHROPIC_API_KEY`: コード生成用のClaude APIキー（末尾の改行文字がないことを確認）
- `GITHUB_ACCESS_TOKEN`: リポジトリ操作用の`repo`スコープを持つGitHub個人アクセストークン

### Confluence連携環境変数（オプショナル）

Confluence連携機能を使用する場合、以下の環境変数を追加設定してください：
- `CONFLUENCE_URL`: ConfluenceインスタンスのURL（例：https://company.atlassian.net/wiki）
- `CONFLUENCE_USERNAME`: Confluenceログイン用メールアドレス
- `CONFLUENCE_API_TOKEN`: Confluence API トークン
- `CONFLUENCE_SPACE_KEY`: デフォルトスペースキー（デフォルト：DEV）

環境変数は`setup-env.sh`スクリプトで設定されます。

## アプリケーションの実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
source setup-env.sh

# ボットを実行
python aibot.py
```

ボットはFlaskを使用してHTTPモードで実行され、ポート3000でリッスンします（PORT環境変数で設定可能）。Slack webhookリクエスト用の`/slack/commands`エンドポイントを公開します。

## 依存関係

必要なPythonパッケージ（`requirements.txt`を参照）：
- `slack-bolt`: Slackアプリフレームワーク
- `anthropic`: Claude APIクライアント
- `PyGithub`: GitHub APIラッパー
- `flask`: HTTPサーバー用Webフレームワーク
- `requests`: Slack response_url通信用HTTPライブラリ
- `atlassian-python-api`: Confluence API操作
- `beautifulsoup4`: HTML解析（ページ内容抽出用）
- `markdown`: マークダウン生成

## 使用パターン

### 従来の開発機能

Slackコマンド形式：`/develop [オーナー/リポジトリ名] の [ファイルパス] に [指示]`

例：`/develop sk8metalme/test-repo の main.py に HelloWorldを出力する機能を追加`

ボットは以下の処理を行います：
1. 指定されたGitHubリポジトリから現在のコードを取得
2. コードと指示をClaudeに送信して修正
3. 生成された変更内容で新しいブランチとプルリクエストを作成
4. プルリクエストのURLをSlackで応答

### 新機能：設計ドキュメント作成

#### 従来版
Slackコマンド形式：`/design [プロジェクト名] の [機能名] について [要件・制約]`

例：`/design my-app の ユーザー認証機能 について JWT認証を使用し、ログイン・ログアウト・パスワードリセット機能を含む`

#### MCP版（推奨）
Slackコマンド形式：`/design-mcp [プロジェクト名] の [機能名] について [要件・制約]`

例：`/design-mcp my-app の ユーザー認証機能 について JWT認証を使用し、ログイン・ログアウト・パスワードリセット機能を含む`

ボットは以下の処理を行います：
1. Claude APIで詳細な設計ドキュメントを生成
2. Atlassian MCP Server経由でConfluenceに設計ドキュメントページを作成
3. 設計書URLをSlackで応答

### 新機能：設計ベース開発

#### 従来版
Slackコマンド形式：`/develop-from-design [confluence-url] の [ファイルパス] に実装`

例：`/develop-from-design https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装`

#### MCP版（推奨）
Slackコマンド形式：`/develop-from-design-mcp [confluence-url] の [ファイルパス] に実装`

例：`/develop-from-design-mcp https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装`

ボットは以下の処理を行います：
1. Atlassian MCP Server経由でConfluenceのURLから設計ドキュメントを取得
2. 設計内容に基づいてClaude APIでコードを生成
3. 生成されたコードをSlackで応答（将来：GitHubへの自動PR作成）

### 新機能：Confluence検索

Slackコマンド形式：`/confluence-search [検索クエリ] [in:スペースキー]`

例：`/confluence-search ユーザー認証 in:DEV`

ボットは以下の処理を行います：
1. Atlassian MCP Server経由でConfluenceページを検索
2. 検索結果をSlackで応答

## トラブルシューティング

### よくある問題

1. **404 GitHubエラー**: リポジトリが存在し、GitHubトークンがアクセス権限を持っていることを確認
2. **不正なヘッダー値**: APIキーに末尾の改行文字がないことを確認
3. **Slackスコープ不足**: SlackボットがOAuthスコープを持っていることを確認
4. **リクエスト署名検証**: SLACK_SIGNING_SECRETが正しく設定されていることを確認

### Slackボット設定要件

Slackアプリには以下が必要です：
- **OAuthスコープ**: `commands`（スラッシュコマンド用）
- **スラッシュコマンド**: サーバーの`/slack/commands`エンドポイントを指す以下のコマンド
  - `/develop`: 従来の開発機能
  - `/design`: 設計ドキュメント作成（従来版）
  - `/design-mcp`: 設計ドキュメント作成（MCP版）
  - `/develop-from-design`: 設計ベース開発（従来版）
  - `/develop-from-design-mcp`: 設計ベース開発（MCP版）
  - `/confluence-search`: Confluence検索
- **リクエストURL**: `https://your-server.com/slack/commands`

## MCP（Model Context Protocol）について

### 概要
このボットは、Atlassian公式のRemote MCP Server（`https://mcp.atlassian.com/v1/sse`）を使用して、より簡素化されたConfluence連携を実現しています。

### MCP使用の利点
- **コード複雑性の削減**: 従来比75%のコード削減
- **依存関係の簡素化**: 3つの外部ライブラリが不要
- **認証の自動化**: OAuth認証がMCPサーバーで自動処理
- **エラーハンドリングの簡素化**: 標準的なAnthropic APIエラー処理のみ

### 前提条件
- Claude Team/Enterprise プラン（MCPサポート）
- Atlassian Cloud アカウント
- Confluence Cloud インスタンス

### ハイブリッド実装
現在の実装では、MCP優先でフォールバック機能を提供します：
1. MCPを使用した処理を試行
2. 失敗した場合、従来の直接API呼び出しにフォールバック
3. エラーハンドリングと結果の統一

詳細は `MCP_SIMPLIFICATION.md` を参照してください。
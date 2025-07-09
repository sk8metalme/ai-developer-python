# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリのコードを扱う際のガイダンスを提供します。

## プロジェクト概要

これは、GitHubとAnthropic社のClaude APIと連携するSlack AI開発ボットです。ボットはSlackからのスラッシュコマンドを受け取り、自動的にコード変更を生成し、GitHubリポジトリにプルリクエストを作成します。

## アーキテクチャ

アプリケーションは以下のコンポーネントで構成されています：

- **Slack連携**: Slack BoltフレームワークとSocket Modeを使用して複数のスラッシュコマンドを処理（`/develop`, `/design`, `/design-mcp`, `/develop-from-design`, `/develop-from-design-mcp`, `/confluence-search`）
- **GitHub連携**: PyGithubライブラリを使用したリポジトリ操作（ファイル読み取り、ブランチ作成、PR作成）
- **AI連携**: 自然言語指示に基づくコード生成のためのAnthropic Claude API
- **Confluence連携**: 
  - **MCP版**: リモートMCPサーバー (https://mcp.atlassian.com/v1/sse) を使用した実装（フォールバック付き）
  - **Direct API版**: atlassian-python-api を使用した直接API呼び出し
- **非同期処理**: Slackの3秒タイムアウトをブロックしない長時間実行タスクの処理
- **Socket Mode**: WebSocketベースの双方向通信（外部エンドポイント不要）

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
- `AtlassianMCPClient`: sooperset/mcp-atlassianとの連携クライアント（フォールバック機能付き）
- `create_confluence_page_mcp()`: MCP経由でConfluenceページを作成（直接API呼び出しにフォールバック）
- `get_confluence_page_mcp()`: MCP経由でConfluenceページ内容を取得（直接API呼び出しにフォールバック）
- `search_confluence_pages_mcp()`: MCP経由でConfluenceページを検索（直接API呼び出しにフォールバック）
- `generate_design_document_mcp()`: MCP対応版設計ドキュメント生成

## 環境設定

### 基本環境変数（必須）

アプリケーションには4つの基本環境変数が必要です：
- `SLACK_BOT_TOKEN`: Slackボット認証トークン（`commands`スコープが必要）
- `SLACK_APP_TOKEN`: Socket Mode用のApp-Level Token（`connections:write`スコープが必要）
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

ボットはSocket Modeで実行され、SlackとWebSocket接続を確立します。外部エンドポイントは不要です。

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
2. リモートMCPサーバー (https://mcp.atlassian.com/v1/sse) 経由でConfluenceに設計ドキュメントページを作成
3. 設計書URLをSlackで応答

### 新機能：設計ベース開発

#### 従来版
Slackコマンド形式：`/develop-from-design [confluence-url] の [ファイルパス] に実装`

例：`/develop-from-design https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装`

#### MCP版（推奨）
Slackコマンド形式：`/develop-from-design-mcp [confluence-url] の [ファイルパス] に実装`

例：`/develop-from-design-mcp https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装`

ボットは以下の処理を行います：
1. リモートMCPサーバー (https://mcp.atlassian.com/v1/sse) 経由でConfluenceのURLから設計ドキュメントを取得
2. 設計内容に基づいてClaude APIでコードを生成
3. 生成されたコードをSlackで応答（将来：GitHubへの自動PR作成）

### 新機能：Confluence検索

Slackコマンド形式：`/confluence-search [検索クエリ] [in:スペースキー]`

例：`/confluence-search ユーザー認証 in:DEV`

ボットは以下の処理を行います：
1. リモートMCPサーバー (https://mcp.atlassian.com/v1/sse) 経由でConfluenceページを検索
2. 検索結果をSlackで応答

## トラブルシューティング

### よくある問題

1. **404 GitHubエラー**: リポジトリが存在し、GitHubトークンがアクセス権限を持っていることを確認
2. **不正なヘッダー値**: APIキーに末尾の改行文字がないことを確認
3. **Slackスコープ不足**: SlackボットがOAuthスコープを持っていることを確認
4. **リクエスト署名検証**: SLACK_SIGNING_SECRETが正しく設定されていることを確認

### Slackボット設定要件

Slackアプリには以下が必要です：
- **Socket Mode**: 有効化必須
- **App-Level Token**: `connections:write`スコープ付きトークンが必要
- **OAuthスコープ**: `commands`（スラッシュコマンド用）
- **スラッシュコマンド**: 以下のコマンド（Request URLは不要）
  - `/develop`: 従来の開発機能
  - `/design`: 設計ドキュメント作成（従来版）
  - `/design-mcp`: 設計ドキュメント作成（MCP版）
  - `/develop-from-design`: 設計ベース開発（従来版）
  - `/develop-from-design-mcp`: 設計ベース開発（MCP版）
  - `/confluence-search`: Confluence検索

## MCP（Model Context Protocol）について

### 概要
このボットは、リモートMCPサーバー (https://mcp.atlassian.com/v1/sse) を使用してConfluence連携を実現しています。SSE (Server-Sent Events) プロトコルでリモートサーバーと通信し、フォールバック機能として直接API呼び出しを使用しています。

### MCP実装の特徴
- **リモートMCPサーバー**: https://mcp.atlassian.com/v1/sse を使用
- **SSEプロトコル**: Server-Sent Events でリアルタイム通信
- **フォールバック機能**: エラー時は直接API呼び出しにフォールバック
- **依存関係**: sseclient-py、httpx、aiohttp、atlassian-python-api、beautifulsoup4、markdownライブラリを使用
- **認証**: 環境変数による認証情報の管理

### 前提条件
- リモートMCPサーバーへのアクセス権限
- Atlassian Cloud アカウント
- Confluence Cloud インスタンス
- 適切な環境変数設定

### 実装の詳細
現在の実装では以下の動作を行います：
1. リモートMCPサーバーとのセッション確立
2. SSEプロトコルでリアルタイム通信
3. エラー時は直接API呼び出しにフォールバック
4. 非同期処理でパフォーマンスを最適化

### 環境変数
- `ATLASSIAN_MCP_API_KEY`: リモートMCPサーバーのAPIキー（オプション）
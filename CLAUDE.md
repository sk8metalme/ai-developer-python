# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリのコードを扱う際のガイダンスを提供します。

## プロジェクト概要

これは、GitHubとAnthropic社のClaude APIと連携するSlack AI開発ボットです。ボットはSlackからのスラッシュコマンドを受け取り、自動的にコード変更を生成し、GitHubリポジトリにプルリクエストを作成します。

## アーキテクチャ

アプリケーションは単一のPythonファイル（`aibot.py`）で構成され、以下を実装しています：

- **Slack連携**: Slack BoltフレームワークとFlaskアダプターを使用して`/develop`スラッシュコマンドを処理
- **GitHub連携**: PyGithubライブラリを使用したリポジトリ操作（ファイル読み取り、ブランチ作成、PR作成）
- **AI連携**: 自然言語指示に基づくコード生成のためのAnthropic Claude API
- **非同期処理**: Slackの3秒タイムアウトをブロックしない長時間実行タスクの処理
- **HTTPサーバー**: Slack webhookリクエストを受信するFlaskベースのHTTPサーバー

## 主要コンポーネント

- `get_repo_content()`: GitHubリポジトリからファイル内容を取得
- `create_github_pr()`: 新しいブランチを作成し、ファイルを更新し、プルリクエストを作成
- `process_development_task()`: ワークフロー全体を統制するメインの非同期タスクハンドラー
- `handle_develop_command()`: 即座に応答するSlackコマンドハンドラー

## 環境設定

アプリケーションには4つの環境変数が必要です：
- `SLACK_BOT_TOKEN`: Slackボット認証トークン（`commands`スコープが必要）
- `SLACK_SIGNING_SECRET`: リクエスト検証用のSlackアプリ署名シークレット
- `ANTHROPIC_API_KEY`: コード生成用のClaude APIキー（末尾の改行文字がないことを確認）
- `GITHUB_ACCESS_TOKEN`: リポジトリ操作用の`repo`スコープを持つGitHub個人アクセストークン

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

## 使用パターン

Slackコマンド形式：`/develop [オーナー/リポジトリ名] の [ファイルパス] に [指示]`

例：`/develop sk8metalme/test-repo の main.py に HelloWorldを出力する機能を追加`

ボットは以下の処理を行います：
1. 指定されたGitHubリポジトリから現在のコードを取得
2. コードと指示をClaudeに送信して修正
3. 生成された変更内容で新しいブランチとプルリクエストを作成
4. プルリクエストのURLをSlackで応答

## トラブルシューティング

### よくある問題

1. **404 GitHubエラー**: リポジトリが存在し、GitHubトークンがアクセス権限を持っていることを確認
2. **不正なヘッダー値**: APIキーに末尾の改行文字がないことを確認
3. **Slackスコープ不足**: SlackボットがOAuthスコープを持っていることを確認
4. **リクエスト署名検証**: SLACK_SIGNING_SECRETが正しく設定されていることを確認

### Slackボット設定要件

Slackアプリには以下が必要です：
- **OAuthスコープ**: `commands`（スラッシュコマンド用）
- **スラッシュコマンド**: サーバーの`/slack/commands`エンドポイントを指す`/develop`
- **リクエストURL**: `https://your-server.com/slack/commands`
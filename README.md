# Slack AI開発ボット

Anthropic社のClaude APIを使用して、自動的にコード変更を生成し、GitHubリポジトリにプルリクエストを作成するSlackボットです。

## 機能

- 🤖 **AI駆動コード生成**: 自然言語指示に基づいてClaude APIでコードを生成
- 📱 **Slack連携**: Slackの`/develop`スラッシュコマンドに応答
- 🔗 **GitHub連携**: ブランチ、コミット、プルリクエストを自動作成
- ⚡ **非同期処理**: Slackレスポンスをブロックしない長時間実行タスクの処理
- 🛡️ **セキュリティ**: リクエスト署名検証と適切なOAuthスコープ

## クイックスタート

### 1. 前提条件

- Python 3.8+
- 管理者権限のあるSlackワークスペース
- リポジトリアクセス権限のあるGitHubアカウント
- Anthropic APIキー

### 2. インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-username/ai-developer-python.git
cd ai-developer-python

# 依存関係をインストール
pip install -r requirements.txt
```

### 3. 設定

1. **環境変数を`setup-env.sh`で設定**:
   ```bash
   export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
   export SLACK_SIGNING_SECRET="your-slack-signing-secret"
   export ANTHROPIC_API_KEY="sk-ant-your-anthropic-api-key"
   export GITHUB_ACCESS_TOKEN="ghp_your-github-token"
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

Slackで以下の形式で`/develop`コマンドを使用してください：

```
/develop [オーナー/リポジトリ] の [ファイルパス] に [指示]
```

### 使用例

```
/develop sk8metalme/test-repo の main.py に HelloWorldを出力する機能を追加
```

```
/develop myuser/myapp の app.py に ログイン機能を追加
```

## 動作の仕組み

1. **コマンド処理**: ボットがSlackからスラッシュコマンドを受信
2. **リポジトリアクセス**: 指定されたGitHubリポジトリから現在のコードを取得
3. **AI生成**: コードと指示をClaude APIに送信して修正
4. **ブランチ作成**: 生成された変更内容で新しいブランチを作成
5. **プルリクエスト**: 修正されたコードでPRを作成
6. **通知**: SlackでPR URLを応答

## アーキテクチャ

- **aibot.py**: メインアプリケーションファイル
- **Flaskサーバー**: SlackからのHTTPリクエストを処理
- **スレッド処理**: 長時間実行タスクの非同期処理
- **エラーハンドリング**: 包括的なログ記録とエラー回復

## 依存関係

- `slack-bolt`: Slackアプリフレームワーク
- `anthropic`: Claude APIクライアント
- `PyGithub`: GitHub APIラッパー
- `flask`: Webフレームワーク
- `requests`: HTTPライブラリ

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
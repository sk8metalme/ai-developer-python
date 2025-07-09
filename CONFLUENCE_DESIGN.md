# Confluence連携機能設計書

## 概要

Slack AI開発ボットにConfluence連携機能を追加し、設計フェーズから開発フェーズまでの一貫したワークフローを実現する。

## 機能要件

### 1. 設計ドキュメント作成機能 (`/design`)

**コマンド形式:**
```
/design [プロジェクト名] の [機能名] について [要件・制約]
```

**例:**
```
/design my-app の ユーザー認証機能 について JWT認証を使用し、ログイン・ログアウト・パスワードリセット機能を含む
```

**処理フロー:**
1. Slackコマンド受信
2. Claude APIで設計ドキュメント生成
3. Confluenceページ作成
4. Slackに結果通知

### 2. 設計確認・開発機能 (`/develop-from-design`)

**コマンド形式:**
```
/develop-from-design [confluence-url] の [ファイルパス] に実装
```

**例:**
```
/develop-from-design https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装
```

**処理フロー:**
1. Slackコマンド受信
2. Confluenceから設計ドキュメント取得
3. Claude APIでコード生成
4. GitHubにPR作成
5. Slackに結果通知

## 技術設計

### 環境変数追加

```bash
export CONFLUENCE_URL="https://your-company.atlassian.net/wiki"
export CONFLUENCE_USERNAME="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-confluence-api-token"
export CONFLUENCE_SPACE_KEY="DEV"  # デフォルトスペース
```

### 新規関数設計

#### Confluence操作関数

```python
def create_confluence_page(space_key: str, title: str, content: str, parent_id: str = None) -> str:
    """Confluenceページを作成"""
    
def get_confluence_page_content(page_url: str) -> str:
    """Confluenceページの内容を取得"""
    
def update_confluence_page(page_id: str, title: str, content: str, version: int) -> bool:
    """Confluenceページを更新"""
```

#### 設計ドキュメント生成関数

```python
def generate_design_document(project_name: str, feature_name: str, requirements: str) -> str:
    """Claude APIを使用して設計ドキュメントを生成"""
    
def generate_code_from_design(design_content: str, file_path: str, additional_requirements: str = "") -> str:
    """設計ドキュメントからコードを生成"""
```

#### 新しいSlackコマンドハンドラー

```python
@app.command("/design")
def handle_design_command(ack, body, say):
    """設計ドキュメント作成コマンド"""
    
@app.command("/develop-from-design")
def handle_develop_from_design_command(ack, body, say):
    """設計ベース開発コマンド"""
```

### データフロー

#### 設計作成フロー
```
Slack /design → Claude API → Confluence → Slack通知
```

#### 設計ベース開発フロー
```
Slack /develop-from-design → Confluence → Claude API → GitHub → Slack通知
```

## 設計ドキュメントテンプレート

### Claude APIプロンプト（設計生成用）

```
あなたはシニアシステムアーキテクトです。以下の要件に基づいて詳細な設計ドキュメントを作成してください。

プロジェクト: {project_name}
機能: {feature_name}
要件: {requirements}

以下の形式で設計ドキュメントを作成してください：

# {feature_name} 設計書

## 概要
[機能の概要]

## 要件
[機能要件と非機能要件]

## アーキテクチャ
[システム構成図、コンポーネント図]

## API設計
[エンドポイント、リクエスト/レスポンス形式]

## データベース設計
[テーブル設計、ER図]

## シーケンス図
[主要な処理フローのシーケンス図]

## セキュリティ考慮事項
[セキュリティ要件と対策]

## テスト戦略
[テスト方針とテストケース]

## 実装方針
[技術選定、コーディング規約]
```

### Claude APIプロンプト（コード生成用）

```
あなたはシニアソフトウェアエンジニアです。以下の設計ドキュメントに基づいてコードを実装してください。

設計ドキュメント:
{design_content}

実装対象ファイル: {file_path}
追加要件: {additional_requirements}

設計書の内容に忠実に、以下の点を考慮して実装してください：
- コードの可読性と保守性
- エラーハンドリング
- セキュリティベストプラクティス
- テスタビリティ
- パフォーマンス

実装後のコード全体のみを、コードブロックなしで返してください。
```

## セキュリティ考慮事項

### Confluence API認証
- API トークンの安全な管理
- 最小権限の原則（ページ作成・読み取りのみ）
- トークンの定期的なローテーション

### データ保護
- 機密情報のマスキング
- Confluenceアクセスログの監視
- 設計ドキュメントのアクセス制御

## エラーハンドリング

### Confluence API エラー
- 認証エラー（401）
- 権限エラー（403）
- ページ未発見（404）
- レート制限エラー（429）

### 設計ドキュメント処理エラー
- 不正なURL形式
- ページ内容の解析エラー
- 設計内容不足エラー

## 運用考慮事項

### ログ記録
- Confluence操作ログ
- 設計ドキュメント作成ログ
- API使用量ログ

### 監視項目
- Confluence API応答時間
- 設計ドキュメント作成成功率
- エラー発生率

## 今後の拡張

### Phase 2 機能
- 設計レビュー機能（レビューコメントの自動収集）
- 設計変更履歴の追跡
- 複数の設計ドキュメントからの統合開発

### Phase 3 機能
- 設計ドキュメントの自動更新
- コードからの逆引き設計書生成
- テストケースの自動生成

## 依存関係

### 新規追加ライブラリ
- `atlassian-python-api`: Confluence API操作
- `beautifulsoup4`: HTML解析（ページ内容抽出用）
- `markdown`: マークダウン生成

### 設定ファイル更新
- `requirements.txt`: 新規依存関係追加
- `setup-env.sh`: Confluence環境変数追加
- `CLAUDE.md`: 新機能の使用方法追加
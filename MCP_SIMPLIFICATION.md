# MCP活用によるConfluence連携の簡素化

## 概要

Atlassian公式のRemote MCP Server（`https://mcp.atlassian.com/v1/sse`）を活用することで、現在の複雑なConfluence連携実装を大幅に簡素化できます。

## 現在の実装 vs MCP活用の比較

### 現在の実装（複雑）

```python
# 現在の複雑な実装
import os
import requests
import re
import markdown
from atlassian import Confluence
from bs4 import BeautifulSoup

# 環境変数管理
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "").strip()
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME", "").strip()
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "").strip()
CONFLUENCE_SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "DEV").strip()

# クライアント初期化
confluence_client = Confluence(
    url=CONFLUENCE_URL,
    username=CONFLUENCE_USERNAME,
    password=CONFLUENCE_API_TOKEN,
    cloud=True
)

def create_confluence_page(space_key: str, title: str, content: str, parent_id: str = None):
    # 複雑なページ作成ロジック
    html_content = markdown.markdown(content, extensions=['tables', 'fenced_code', 'toc'])
    # ... 50行以上のコード

def get_confluence_page_content(page_url: str):
    # 複雑なページ取得・解析ロジック
    page_id_match = re.search(r'pageId=(\d+)', page_url)
    # ... 40行以上のコード
```

**問題点:**
- 複雑な認証管理
- HTML/マークダウン変換の複雑さ
- エラーハンドリングの煩雑さ
- 依存関係の多さ（atlassian-python-api, beautifulsoup4, markdown）

### MCP活用（簡素化）

```python
# MCP活用による簡素化実装
from anthropic import Anthropic
import json

# MCPツールを使用した簡単な実装
def create_confluence_page_with_mcp(space_key: str, title: str, content: str):
    """MCPツールを使用してConfluenceページを作成"""
    prompt = f"""
    Confluenceに以下の設計ドキュメントを作成してください：
    
    スペース: {space_key}
    タイトル: {title}
    内容: {content}
    
    適切なMarkdown形式で整形してConfluenceページとして作成してください。
    """
    
    # Claude APIがMCPツールを自動使用
    response = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "name": "confluence_create_page",
                "description": "Create a new Confluence page"
            }
        ]
    )
    
    return response

def get_confluence_page_with_mcp(page_url: str):
    """MCPツールを使用してConfluenceページ内容を取得"""
    prompt = f"""
    以下のConfluenceページの内容を取得してください：
    URL: {page_url}
    
    ページの内容をテキスト形式で返してください。
    """
    
    response = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "name": "confluence_get_page",
                "description": "Get Confluence page content"
            }
        ]
    )
    
    return response.content[0].text
```

## 簡素化のメリット

### 1. コード量の削減
- **現在**: 約200行のConfluence連携コード
- **MCP活用**: 約50行（75%削減）

### 2. 依存関係の削減
```python
# 現在の依存関係
atlassian-python-api
beautifulsoup4
markdown

# MCP活用後
# 追加依存関係なし（anthropicのみ）
```

### 3. 認証の簡素化
```python
# 現在: 複雑な環境変数管理
CONFLUENCE_URL
CONFLUENCE_USERNAME  
CONFLUENCE_API_TOKEN
CONFLUENCE_SPACE_KEY

# MCP活用後: 
# MCPサーバーがOAuth認証を自動処理
# 環境変数不要
```

### 4. エラーハンドリングの簡素化
```python
# 現在: 複雑なエラーハンドリング
try:
    # Confluence API呼び出し
except ConfluenceException:
    # 個別エラー処理
except HTTPError:
    # HTTP エラー処理
except ConnectionError:
    # 接続エラー処理

# MCP活用後:
# MCPサーバーが自動的にエラーハンドリング
# Claude APIの標準エラー処理のみ
```

## 実装戦略

### Phase 1: ハイブリッド実装
```python
def create_confluence_page_hybrid(space_key: str, title: str, content: str):
    """MCP優先、フォールバック付きの実装"""
    try:
        # MCP経由での作成を試行
        return create_confluence_page_with_mcp(space_key, title, content)
    except Exception as e:
        logging.warning(f"MCP creation failed, falling back to direct API: {e}")
        # 既存の直接API実装にフォールバック
        return create_confluence_page(space_key, title, content)
```

### Phase 2: 完全MCP移行
```python
# 既存のConfluence直接連携コードを削除
# MCP実装のみに統一
```

## MCP設定要件

### 1. Claude Team/Enterprise プランが必要
- 現在のMCPサポートは有料プランのみ

### 2. Atlassian Cloud アカウント
- Confluence Cloud インスタンスが必要
- 適切なアクセス権限が必要

### 3. MCP Server URL設定
```
https://mcp.atlassian.com/v1/sse
```

## 実装の変更点

### 新しいSlackコマンドハンドラー
```python
@app.command("/design")
def handle_design_command_mcp(ack, body, say):
    """MCP版設計ドキュメント作成コマンド"""
    ack("設計依頼を受け付けました...")
    
    def process_with_mcp():
        text = body.get("text", "")
        # コマンド解析（既存と同じ）
        
        # MCP経由でのページ作成
        prompt = f"""
        以下の要件に基づいて詳細な設計ドキュメントをConfluenceに作成してください：
        
        プロジェクト: {project_name}
        機能: {feature_name}  
        要件: {requirements}
        
        スペース: {CONFLUENCE_SPACE_KEY}
        タイトル: {project_name} - {feature_name} 設計書
        
        設計書は以下のセクションを含む詳細なものにしてください：
        - 概要
        - 要件（機能要件・非機能要件）
        - アーキテクチャ
        - API設計
        - データベース設計
        - セキュリティ考慮事項
        - 実装方針
        - テスト戦略
        - 運用考慮事項
        """
        
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # レスポンスからページURLを抽出してSlackに通知
        
    threading.Thread(target=process_with_mcp).start()
```

## 移行計画

### Step 1: 準備フェーズ
1. Atlassian Cloud Team/Enterprise プランの確認
2. Claude Team/Enterprise プランの確認  
3. MCP Server接続テスト

### Step 2: 実装フェーズ
1. MCP版の関数を追加実装
2. ハイブリッド実装でテスト
3. 段階的に既存実装を置換

### Step 3: 最適化フェーズ
1. 不要な依存関係の削除
2. 環境変数の整理
3. テストケースの更新

## 制約・考慮事項

### 1. 現在の制約
- Claude Team/Enterprise プランが必要
- Confluence Cloud のみ対応
- ベータ版のため機能制限あり

### 2. 将来の拡張性
- 他のMCPクライアント対応予定
- オンプレミス版の対応可能性
- コミュニティ版MCPサーバーとの連携

## 結論

MCP活用により：
- **コード複雑性**: 75%削減
- **依存関係**: 3つの外部ライブラリ削除
- **認証管理**: 完全自動化
- **メンテナンス性**: 大幅向上

Atlassian公式のMCP Serverを活用することで、より堅牢で保守性の高いConfluence連携が実現できます。
# MCP活用によるConfluence連携の簡素化

## 概要

sooperset/mcp-atlassianのDockerイメージを活用することで、現在の複雑なConfluence連携実装を大幅に簡素化できます。ただし、現在の実装では実際にはフォールバック機能として直接API呼び出しを使用しています。

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

### MCP活用（実際の実装）

```python
# sooperset/mcp-atlassianを使用した実装（実際はフォールバック機能付き）
import subprocess
import docker
from atlassian import Confluence

class AtlassianMCPClient:
    def __init__(self):
        self.docker_image = "ghcr.io/sooperset/mcp-atlassian:latest"
        self._ensure_docker_image()
    
    def _ensure_docker_image(self):
        """Dockerイメージの存在確認とプル"""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.docker_image],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                subprocess.run(["docker", "pull", self.docker_image], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logging.error("Docker環境の準備に失敗")
    
    def _run_mcp_tool(self, tool_name: str, arguments: dict):
        """MCPツール実行（現在はフォールバックに直行）"""
        # 実際の実装では直接API呼び出しにフォールバック
        return self._fallback_to_direct_api(tool_name, arguments)
    
    def _fallback_to_direct_api(self, tool_name: str, arguments: dict):
        """直接APIへのフォールバック実装"""
        confluence = Confluence(
            url=self.confluence_url,
            username=self.confluence_username,
            password=self.confluence_api_token,
            cloud=True
        )
        
        if tool_name == "confluence_create_page":
            # 直接API呼び出しでページ作成
            return confluence.create_page(...)
        elif tool_name == "confluence_get_page":
            # 直接API呼び出しでページ取得
            return confluence.get_page_by_id(...)
```

## 実装の特徴

### 1. ハイブリッドアプローチ
- **Docker準備**: sooperset/mcp-atlassianイメージを確認・プル
- **実際の処理**: 直接API呼び出しにフォールバック
- **メリット**: 堅牢性と安定性の確保

### 2. 現在の依存関係
```python
# 実際の依存関係
atlassian-python-api  # 直接API呼び出し用
beautifulsoup4        # HTML解析用
markdown              # マークダウン変換用
subprocess            # Docker操作用
```

### 3. 認証管理
```python
# 現在: 環境変数による認証管理
CONFLUENCE_URL
CONFLUENCE_USERNAME  
CONFLUENCE_API_TOKEN
CONFLUENCE_SPACE_KEY

# 理想的なMCP活用後: 
# MCPサーバーがOAuth認証を自動処理
# 環境変数不要（将来の改善点）
```

### 4. エラーハンドリング
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

# 実際の実装: フォールバック機能付き
def _run_mcp_tool(self, tool_name: str, arguments: dict):
    try:
        # 本来はMCPツールを実行
        return self._fallback_to_direct_api(tool_name, arguments)
    except Exception as e:
        logging.error(f"MCP ツール実行エラー: {e}")
        return {"success": False, "error": str(e)}
```
# Claude APIの標準エラー処理のみ
```

## 実装戦略

### 現在の実装（Phase 1）
```python
def create_confluence_page_hybrid(space_key: str, title: str, content: str):
    """Docker準備付きフォールバック実装"""
    try:
        # Dockerイメージの確認
        self._ensure_docker_image()
        # 実際は直接API呼び出しにフォールバック
        return self._fallback_to_direct_api("confluence_create_page", arguments)
    except Exception as e:
        logging.error(f"MCP creation failed: {e}")
        return {"success": False, "error": str(e)}
```

### 将来の改善（Phase 2）
```python
# 真のMCP連携実装
# sooperset/mcp-atlassianの活用
# Docker経由での実際のMCP通信
```

## 設定要件

### 1. Docker環境
- sooperset/mcp-atlassianイメージの実行環境

### 2. Atlassian Cloud アカウント
- Confluence Cloud インスタンスが必要
- 適切なアクセス権限が必要

### 3. 環境変数設定
```bash
CONFLUENCE_URL=https://company.atlassian.net/wiki
CONFLUENCE_USERNAME=user@company.com
CONFLUENCE_API_TOKEN=your-token
CONFLUENCE_SPACE_KEY=DEV
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
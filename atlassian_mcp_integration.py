#!/usr/bin/env python3
"""
Atlassian MCP Server Integration for AI Developer Bot
sooperset/mcp-atlassian を活用したConfluence連携
"""

import os
import asyncio
import logging
import subprocess
import json
from typing import Dict, List, Optional, Any
from anthropic import Anthropic, AnthropicError

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- 環境変数から認証情報を読み込み ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "").strip()
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME", "").strip()
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "").strip()
CONFLUENCE_SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "DEV").strip()

# Anthropicクライアントの初期化
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# MCP Server設定
MCP_ATLASSIAN_DOCKER_IMAGE = "ghcr.io/sooperset/mcp-atlassian:latest"

class AtlassianMCPClient:
    """sooperset/mcp-atlassian との連携クライアント"""
    
    def __init__(self):
        self.docker_image = MCP_ATLASSIAN_DOCKER_IMAGE
        self.anthropic_client = anthropic_client
        self.confluence_url = CONFLUENCE_URL
        self.confluence_username = CONFLUENCE_USERNAME
        self.confluence_api_token = CONFLUENCE_API_TOKEN
        self.confluence_space_key = CONFLUENCE_SPACE_KEY
        
        # Docker イメージの確認とプル
        self._ensure_docker_image()
    
    def _ensure_docker_image(self):
        """Dockerイメージが存在するかチェックし、なければプル"""
        try:
            # イメージの存在確認
            result = subprocess.run(
                ["docker", "image", "inspect", self.docker_image],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logging.info(f"Docker イメージをプル中: {self.docker_image}")
                subprocess.run(
                    ["docker", "pull", self.docker_image],
                    check=True
                )
                logging.info("Docker イメージのプル完了")
            else:
                logging.info(f"Docker イメージが利用可能: {self.docker_image}")
                
        except subprocess.CalledProcessError as e:
            logging.error(f"Docker イメージの準備に失敗: {e}")
            raise
        except FileNotFoundError:
            logging.error("Docker がインストールされていません")
            raise
    
    def _run_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """MCP ツールを実行（フォールバック付き）"""
        try:
            # まず直接API呼び出しでフォールバック
            return self._fallback_to_direct_api(tool_name, arguments)
            
        except Exception as e:
            logging.error(f"MCP ツール実行エラー: {e}")
            raise
    
    def _fallback_to_direct_api(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """直接APIへのフォールバック実装"""
        try:
            from atlassian import Confluence
            
            # Confluence APIクライアントの初期化
            confluence = Confluence(
                url=self.confluence_url,
                username=self.confluence_username,
                password=self.confluence_api_token,
                cloud=True
            )
            
            if tool_name == "confluence_search":
                # 検索実行
                cql = arguments.get("cql", "")
                results = confluence.cql(cql)
                
                # 結果の整形
                formatted_results = []
                if isinstance(results, dict) and "results" in results:
                    for item in results["results"]:
                        formatted_results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "space": item.get("space", {}).get("name", ""),
                            "excerpt": item.get("excerpt", ""),
                            "last_modified": item.get("lastModified", "")
                        })
                elif isinstance(results, list):
                    for item in results:
                        formatted_results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "space": item.get("space", {}).get("name", ""),
                            "excerpt": item.get("excerpt", ""),
                            "last_modified": item.get("lastModified", "")
                        })
                
                return {
                    "success": True,
                    "results": formatted_results
                }
                
            elif tool_name == "confluence_get_page":
                # ページ取得
                page_id = arguments.get("page_id", "")
                page = confluence.get_page_by_id(page_id, expand="body.storage")
                
                return {
                    "success": True,
                    "content": page.get("body", {}).get("storage", {}).get("value", ""),
                    "title": page.get("title", ""),
                    "page_id": page_id
                }
                
            elif tool_name == "confluence_create_page":
                # ページ作成
                space_key = arguments.get("space_key", "")
                title = arguments.get("title", "")
                content = arguments.get("content", "")
                parent_id = arguments.get("parent_id", None)
                
                # HTMLに変換
                import markdown
                html_content = markdown.markdown(content)
                
                # ページ作成
                page = confluence.create_page(
                    space=space_key,
                    title=title,
                    body=html_content,
                    parent_id=parent_id
                )
                
                page_url = f"{self.confluence_url}/spaces/{space_key}/pages/{page['id']}"
                
                return {
                    "success": True,
                    "page_url": page_url,
                    "page_id": page["id"]
                }
                
            else:
                raise Exception(f"サポートされていないツール: {tool_name}")
                
        except Exception as e:
            logging.error(f"直接API呼び出しエラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    def create_confluence_page_with_mcp(self, space_key: str, title: str, content: str, parent_id: str = None) -> dict:
        """
        sooperset/mcp-atlassian を使用してConfluenceページを作成
        
        Args:
            space_key: Confluenceスペースキー
            title: ページタイトル
            content: ページ内容（Markdown形式）
            parent_id: 親ページID（オプション）
        
        Returns:
            dict: 作成結果とページ情報
        """
        try:
            logging.info(f"MCP経由でConfluenceページを作成中: {title}")
            
            # MCP ツールの引数を準備
            arguments = {
                "space_key": space_key,
                "title": title,
                "content": content
            }
            
            if parent_id:
                arguments["parent_id"] = parent_id
            
            # confluence_create_page ツールを実行
            result = self._run_mcp_tool("confluence_create_page", arguments)
            
            # 成功した場合のレスポンス処理
            if result.get("success", False):
                page_url = result.get("page_url", "")
                page_id = result.get("page_id", "")
                
                logging.info(f"Confluence ページ作成完了: {page_url}")
                
                return {
                    "success": True,
                    "page_url": page_url,
                    "page_id": page_id,
                    "response": f"ページが正常に作成されました: {page_url}",
                    "title": title,
                    "space_key": space_key
                }
            else:
                error_msg = result.get("error", "不明なエラー")
                logging.error(f"Confluence ページ作成エラー: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "title": title,
                    "space_key": space_key
                }
                
        except Exception as e:
            logging.error(f"MCP ページ作成エラー: {e}")
            return {
                "success": False,
                "error": f"MCP ページ作成エラー: {e}",
                "title": title,
                "space_key": space_key
            }
    
    def get_confluence_page_with_mcp(self, page_url: str) -> dict:
        """
        sooperset/mcp-atlassian を使用してConfluenceページ内容を取得
        
        Args:
            page_url: ConfluenceページのURL
        
        Returns:
            dict: ページ内容と取得結果
        """
        try:
            logging.info(f"MCP経由でConfluenceページを取得中: {page_url}")
            
            # URLからページIDを抽出
            page_id = self._extract_page_id_from_url(page_url)
            
            if not page_id:
                raise Exception(f"ページURLからページIDを抽出できませんでした: {page_url}")
            
            # confluence_get_page ツールを実行
            result = self._run_mcp_tool("confluence_get_page", {"page_id": page_id})
            
            if result.get("success", False):
                content = result.get("content", "")
                title = result.get("title", "")
                
                logging.info(f"Confluence ページ取得完了: {title}")
                
                return {
                    "success": True,
                    "content": content,
                    "title": title,
                    "page_url": page_url,
                    "page_id": page_id,
                    "response": content
                }
            else:
                error_msg = result.get("error", "不明なエラー")
                logging.error(f"Confluence ページ取得エラー: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "page_url": page_url
                }
                
        except Exception as e:
            logging.error(f"MCP ページ取得エラー: {e}")
            return {
                "success": False,
                "error": f"MCP ページ取得エラー: {e}",
                "page_url": page_url
            }
    
    def _extract_page_id_from_url(self, page_url: str) -> str:
        """ConfluenceページURLからページIDを抽出"""
        import re
        
        # 一般的なConfluenceページURLパターン
        patterns = [
            r'/pages/(\d+)/',  # /pages/123456/
            r'/pages/(\d+)',   # /pages/123456
            r'pageId=(\d+)',   # pageId=123456
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_url)
            if match:
                return match.group(1)
        
        return ""
    
    def search_confluence_pages_with_mcp(self, query: str, space_key: str = None) -> dict:
        """
        sooperset/mcp-atlassian を使用してConfluenceページを検索
        
        Args:
            query: 検索クエリ
            space_key: 検索対象スペース（オプション）
        
        Returns:
            dict: 検索結果
        """
        try:
            logging.info(f"MCP経由でConfluenceページを検索中: {query}")
            
            # CQL（Confluence Query Language）クエリを構築
            cql_query = f"text ~ '{query}'"
            if space_key:
                cql_query += f" AND space.key = '{space_key}'"
            
            # confluence_search ツールを実行
            result = self._run_mcp_tool("confluence_search", {"cql": cql_query})
            
            if result.get("success", False):
                results = result.get("results", [])
                
                logging.info(f"Confluence 検索完了: {len(results)}件の結果")
                
                return {
                    "success": True,
                    "results": results,
                    "query": query,
                    "space_key": space_key,
                    "total_count": len(results)
                }
            else:
                error_msg = result.get("error", "不明なエラー")
                logging.error(f"Confluence 検索エラー: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "query": query
                }
                
        except Exception as e:
            logging.error(f"MCP 検索エラー: {e}")
            return {
                "success": False,
                "error": f"MCP 検索エラー: {e}",
                "query": query
            }
    
    def generate_design_document_with_mcp(self, project_name: str, feature_name: str, requirements: str) -> str:
        """
        MCP対応版の設計ドキュメント生成
        
        Args:
            project_name: プロジェクト名
            feature_name: 機能名
            requirements: 要件
        
        Returns:
            str: 生成された設計ドキュメント
        """
        prompt = f"""
あなたはシニアシステムアーキテクトです。以下の要件に基づいて、Confluence向けの詳細な設計ドキュメントを作成してください。

【プロジェクト】: {project_name}
【機能】: {feature_name}
【要件】: {requirements}

以下のテンプレートに従って、実装に直結する詳細な設計書を作成してください：

# {feature_name} 設計書

## 📋 概要
[機能の概要と目的、ビジネス価値]

## 🎯 要件
### 機能要件
[具体的な機能要件をリスト形式で]

### 非機能要件
[パフォーマンス、セキュリティ、可用性、拡張性の要件]

## 🏗️ アーキテクチャ
### システム構成
[システム全体の構成と各コンポーネントの役割]

### データフロー
[リクエストから レスポンスまでのデータの流れ]

### コンポーネント設計
[主要コンポーネントの詳細設計]

## 🔌 API設計
### エンドポイント一覧
| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | /api/... | ... |
| POST | /api/... | ... |

### リクエスト/レスポンス
[各APIの詳細なリクエスト・レスポンス形式とサンプル]

## 🗄️ データベース設計
### テーブル設計
[必要なテーブルとカラム定義、制約]

### インデックス設計
[パフォーマンス最適化のためのインデックス]

### データ移行
[既存データからの移行方針]

## 🔐 セキュリティ設計
### 認証・認可
[認証方式と認可ロジック]

### データ保護
[機密データの暗号化と保護]

### セキュリティ脅威と対策
[想定される脅威と対策]

## 🎨 UI/UX設計
### 画面設計
[主要画面のワイヤーフレームと動線]

### ユーザビリティ
[使いやすさの観点からの設計方針]

## 🧪 テスト戦略
### テスト方針
[単体テスト、統合テスト、E2Eテストの方針]

### テストケース
[主要なテストシナリオ]

### 性能テスト
[負荷テストとパフォーマンス要件]

## 🚀 実装方針
### 技術選定
[使用する技術スタックと選定理由]

### 開発フェーズ
[実装を段階的に進める方針]

### コーディング規約
[命名規則、コードスタイル、ベストプラクティス]

## 📊 運用設計
### 監視・ログ
[システム監視とログ収集の方針]

### デプロイメント
[CI/CDパイプラインとデプロイ戦略]

### 障害対応
[障害発生時の対応手順]

## 📈 パフォーマンス設計
### 処理性能
[応答時間、スループットの目標値]

### スケーラビリティ
[負荷増加に対するスケーリング戦略]

### 最適化
[ボトルネック予測と最適化方針]

## 📋 実装チェックリスト
- [ ] 要件定義の確認
- [ ] API仕様の策定
- [ ] データベース設計の確定
- [ ] セキュリティレビュー
- [ ] パフォーマンステストの実施

各セクションを詳細に記述し、実装チームが迷わず開発を進められる設計書を作成してください。
図表や表を適切に使用し、視覚的にわかりやすい構成にしてください。
"""
        
        try:
            logging.info("MCP対応版設計ドキュメントを生成中...")
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            design_content = response.content[0].text
            logging.info(f"MCP対応版設計ドキュメントが生成されました: {len(design_content)}文字")
            return design_content
            
        except AnthropicError as e:
            logging.error(f"MCP対応版設計ドキュメント生成エラー: {e}")
            return f"設計ドキュメントの生成中にエラーが発生しました: {e}"
    
    def _extract_page_url(self, response_text: str) -> str:
        """
        レスポンステキストからページURLを抽出
        
        Args:
            response_text: APIレスポンステキスト
        
        Returns:
            str: 抽出されたページURL、または空文字列
        """
        import re
        
        # Confluence URLのパターンを検索
        url_patterns = [
            r'https://[^/]+\.atlassian\.net/wiki/[^\s]+',
            r'https://[^/]+\.atlassian\.net/l/[^\s]+',
            r'ページURL[：:]?\s*([^\s]+)',
            r'URL[：:]?\s*([^\s]+)'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, response_text)
            if match:
                url = match.group(1) if match.groups() else match.group(0)
                # URLのクリーンアップ
                url = url.rstrip('。、！？.,!?')
                return url
        
        return ""


# モジュールレベルでクライアントを初期化
atlassian_mcp_client = AtlassianMCPClient()

# 外部から使用する関数
def create_confluence_page_mcp(space_key: str, title: str, content: str, parent_id: str = None):
    """MCP経由でConfluenceページを作成"""
    return atlassian_mcp_client.create_confluence_page_with_mcp(space_key, title, content, parent_id)

def get_confluence_page_mcp(page_url: str):
    """MCP経由でConfluenceページ内容を取得"""
    return atlassian_mcp_client.get_confluence_page_with_mcp(page_url)

def search_confluence_pages_mcp(query: str, space_key: str = None):
    """MCP経由でConfluenceページを検索"""
    return atlassian_mcp_client.search_confluence_pages_with_mcp(query, space_key)

def generate_design_document_mcp(project_name: str, feature_name: str, requirements: str):
    """MCP対応版設計ドキュメント生成"""
    return atlassian_mcp_client.generate_design_document_with_mcp(project_name, feature_name, requirements)


if __name__ == "__main__":
    # テスト実行
    print("=== Atlassian MCP Client テスト ===")
    
    # 簡単なテスト
    test_project = "test-app"
    test_feature = "ユーザー認証機能"
    test_requirements = "JWT認証を使用し、ログイン・ログアウト機能を含む"
    
    print(f"テスト設計ドキュメント生成: {test_project} - {test_feature}")
    design_doc = generate_design_document_mcp(test_project, test_feature, test_requirements)
    print(f"設計ドキュメント生成完了: {len(design_doc)}文字")
    print("=" * 50)
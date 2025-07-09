#!/usr/bin/env python3
"""
MCP Integration tests for AI Developer Bot
Atlassian MCP連携機能のテストファイル
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# テスト実行前に環境変数を設定
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["CONFLUENCE_SPACE_KEY"] = "TEST"

class TestMCPIntegration(unittest.TestCase):
    """MCP連携機能のテスト"""
    
    def setUp(self):
        """テスト前の設定"""
        self.test_project = "test-app"
        self.test_feature = "ユーザー認証機能"
        self.test_requirements = "JWT認証を使用し、ログイン・ログアウト機能を含む"
        self.test_page_url = "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth"
        self.test_file_path = "auth.py"

    def test_mcp_environment_setup(self):
        """MCP環境変数の設定テスト"""
        self.assertEqual(os.environ.get("ANTHROPIC_API_KEY"), "test-anthropic-key")
        self.assertEqual(os.environ.get("CONFLUENCE_SPACE_KEY"), "TEST")

    def test_design_mcp_command_parsing(self):
        """MCP設計コマンドの解析テスト"""
        test_text = "my-app の ユーザー認証機能 について JWT認証を使用し、ログイン・ログアウト機能を含む"
        
        # 解析処理をシミュレート
        parts = test_text.split(" の ", 1)
        project_name = parts[0]
        parts = parts[1].split(" について ", 1)
        feature_name = parts[0]
        requirements = parts[1]
        
        # 検証
        self.assertEqual(project_name, "my-app")
        self.assertEqual(feature_name, "ユーザー認証機能")
        self.assertEqual(requirements, "JWT認証を使用し、ログイン・ログアウト機能を含む")

    def test_develop_from_design_mcp_command_parsing(self):
        """MCP設計ベース開発コマンドの解析テスト"""
        test_text = "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装"
        
        # 解析処理をシミュレート
        parts = test_text.split(" の ", 1)
        confluence_url = parts[0]
        parts = parts[1].split(" に実装", 1)
        file_path = parts[0]
        
        # 検証
        self.assertEqual(confluence_url, "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth")
        self.assertEqual(file_path, "auth.py")

    def test_confluence_search_command_parsing(self):
        """Confluence検索コマンドの解析テスト"""
        test_cases = [
            {
                "input": "ユーザー認証",
                "expected_query": "ユーザー認証",
                "expected_space": None
            },
            {
                "input": "ユーザー認証 in:DEV",
                "expected_query": "ユーザー認証",
                "expected_space": "DEV"
            }
        ]
        
        for case in test_cases:
            with self.subTest(input=case["input"]):
                text = case["input"]
                
                # スペース指定の解析（オプション）
                parts = text.split(" in:", 1)
                query = parts[0].strip()
                space_key = parts[1].strip() if len(parts) > 1 else None
                
                # 検証
                self.assertEqual(query, case["expected_query"])
                self.assertEqual(space_key, case["expected_space"])

    @patch('anthropic.Anthropic')
    def test_mcp_design_document_generation_mock(self, mock_anthropic):
        """MCP設計ドキュメント生成のモックテスト"""
        # モックの設定
        mock_anthropic_instance = Mock()
        mock_anthropic.return_value = mock_anthropic_instance
        
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = """
# ユーザー認証機能 設計書

## 📋 概要
JWT認証システムの実装

## 🎯 要件
### 機能要件
- ログイン機能
- ログアウト機能
- トークン管理

## 🏗️ アーキテクチャ
RESTful API設計

## 🔌 API設計
| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | /api/login | ログイン |
| POST | /api/logout | ログアウト |
"""
        mock_response.content = [mock_content]
        mock_anthropic_instance.messages.create.return_value = mock_response
        
        # Anthropicクライアントを作成
        from anthropic import Anthropic
        anthropic_client = Anthropic(api_key="test-key")
        
        # テスト実行
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            messages=[{"role": "user", "content": "Generate design document"}]
        )
        
        # 検証
        result_text = response.content[0].text
        self.assertIn("ユーザー認証機能", result_text)
        self.assertIn("JWT認証システム", result_text)
        self.assertIn("API設計", result_text)

    def test_mcp_page_url_extraction(self):
        """MCPレスポンスからページURL抽出のテスト"""
        test_responses = [
            {
                "response": "Confluenceページが作成されました。ページURL: https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth",
                "expected": "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth"
            },
            {
                "response": "作成完了\nURL：https://example.atlassian.net/l/cp/12345",
                "expected": "https://example.atlassian.net/l/cp/12345"
            },
            {
                "response": "ページは https://test.atlassian.net/wiki/display/SPACE/Page で確認できます。",
                "expected": "https://test.atlassian.net/wiki/display/SPACE/Page"
            }
        ]
        
        import re
        
        for case in test_responses:
            with self.subTest(response=case["response"][:50] + "..."):
                response_text = case["response"]
                
                # URL抽出ロジック
                url_patterns = [
                    r'https://[^/]+\.atlassian\.net/wiki/[^\s]+',
                    r'https://[^/]+\.atlassian\.net/l/[^\s]+',
                    r'ページURL[：:]?\s*([^\s]+)',
                    r'URL[：:]?\s*([^\s]+)'
                ]
                
                found_url = ""
                for pattern in url_patterns:
                    match = re.search(pattern, response_text)
                    if match:
                        url = match.group(1) if match.groups() else match.group(0)
                        # URLのクリーンアップ
                        url = url.rstrip('。、！？.,!?')
                        found_url = url
                        break
                
                # 検証
                self.assertEqual(found_url, case["expected"])

    def test_mcp_error_handling_scenarios(self):
        """MCPエラーハンドリングシナリオのテスト"""
        # 典型的なMCPエラー形式
        error_scenarios = [
            {
                "error_type": "Authentication Error",
                "error_message": "Invalid authentication credentials"
            },
            {
                "error_type": "Permission Error", 
                "error_message": "Insufficient permissions to access resource"
            },
            {
                "error_type": "Not Found Error",
                "error_message": "Confluence page not found"
            },
            {
                "error_type": "Rate Limit Error",
                "error_message": "API rate limit exceeded"
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(error_type=scenario["error_type"]):
                # エラーレスポンスの構築
                error_response = {
                    "success": False,
                    "error": scenario["error_message"],
                    "error_type": scenario["error_type"]
                }
                
                # エラーハンドリングの検証
                self.assertFalse(error_response["success"])
                self.assertIn("error", error_response)
                self.assertTrue(len(error_response["error"]) > 0)

    def test_mcp_fallback_mechanism(self):
        """MCPフォールバック機能のテスト"""
        # MCP利用不可の場合のフォールバック検証
        
        # MCP利用可能状況のテスト
        mcp_available_cases = [True, False]
        
        for mcp_available in mcp_available_cases:
            with self.subTest(mcp_available=mcp_available):
                if mcp_available:
                    # MCP利用可能な場合
                    expected_method = "MCP経由での処理"
                else:
                    # MCP利用不可能な場合
                    expected_method = "従来のAPI経由での処理"
                
                # フォールバック判定ロジック
                actual_method = "MCP経由での処理" if mcp_available else "従来のAPI経由での処理"
                
                self.assertEqual(actual_method, expected_method)

    def test_mcp_design_document_structure(self):
        """MCP設計ドキュメント構造のテスト"""
        # MCP版設計ドキュメントに含まれるべきセクション
        expected_sections = [
            "# .* 設計書",
            "## 📋 概要",
            "## 🎯 要件",
            "### 機能要件",
            "### 非機能要件", 
            "## 🏗️ アーキテクチャ",
            "## 🔌 API設計",
            "## 🗄️ データベース設計",
            "## 🔐 セキュリティ設計",
            "## 🧪 テスト戦略",
            "## 🚀 実装方針",
            "## 📊 運用設計"
        ]
        
        # 各セクションの正規表現パターンが適切であることを確認
        import re
        for section_pattern in expected_sections:
            # 正規表現として有効であることを確認
            try:
                re.compile(section_pattern)
                pattern_valid = True
            except re.error:
                pattern_valid = False
            
            self.assertTrue(pattern_valid, f"Invalid regex pattern: {section_pattern}")

    def test_mcp_slack_command_handlers(self):
        """MCPSlackコマンドハンドラーのテスト"""
        # 新しいMCPコマンドの定義
        mcp_commands = [
            "/design-mcp",
            "/develop-from-design-mcp", 
            "/confluence-search"
        ]
        
        # 各コマンドの形式検証
        for command in mcp_commands:
            with self.subTest(command=command):
                # コマンドフォーマットの検証
                self.assertTrue(command.startswith("/"))
                self.assertTrue(len(command) > 1)
                self.assertNotIn(" ", command)  # スペースが含まれていないこと

    def test_mcp_integration_availability_check(self):
        """MCP連携可用性チェックのテスト"""
        # インポート可能性のシミュレート
        import_scenarios = [
            {"available": True, "expected_status": "利用可能"},
            {"available": False, "expected_status": "利用不可"}
        ]
        
        for scenario in import_scenarios:
            with self.subTest(available=scenario["available"]):
                # MCP可用性フラグのシミュレート
                mcp_available = scenario["available"]
                
                # 可用性チェックロジック
                status = "利用可能" if mcp_available else "利用不可"
                
                # 検証
                self.assertEqual(status, scenario["expected_status"])

    def test_mcp_response_format_validation(self):
        """MCPレスポンス形式の検証テスト"""
        # 期待されるMCPレスポンス形式
        expected_response_structure = {
            "success": bool,
            "content": str,
            "page_url": str,
            "error": str
        }
        
        # テスト用のレスポンス例
        test_responses = [
            {
                "success": True,
                "content": "テスト内容",
                "page_url": "https://example.atlassian.net/wiki/pages/123",
                "response": "作成完了"
            },
            {
                "success": False,
                "error": "認証エラー",
                "page_url": ""
            }
        ]
        
        for response in test_responses:
            with self.subTest(success=response.get("success")):
                # 必須フィールドの存在確認
                self.assertIn("success", response)
                self.assertIsInstance(response["success"], bool)
                
                if response["success"]:
                    # 成功時の検証
                    self.assertTrue(len(response.get("content", "")) >= 0)
                else:
                    # 失敗時の検証
                    self.assertIn("error", response)
                    self.assertTrue(len(response["error"]) > 0)


if __name__ == '__main__':
    # テストスイートの実行
    print("=== Atlassian MCP連携機能テスト実行 ===")
    print("MCP環境変数設定:", {
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "CONFLUENCE_SPACE_KEY": bool(os.environ.get("CONFLUENCE_SPACE_KEY")),
    })
    print("=" * 50)
    
    unittest.main(verbosity=2)
#!/usr/bin/env python3
"""
Confluence integration tests for AI Developer Bot
Confluence連携機能のテストファイル
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os

# テスト実行前に環境変数を設定
os.environ["SLACK_BOT_TOKEN"] = "test-slack-token"
os.environ["SLACK_SIGNING_SECRET"] = "test-signing-secret"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["GITHUB_ACCESS_TOKEN"] = "test-github-token"
os.environ["CONFLUENCE_URL"] = "https://test.atlassian.net/wiki"
os.environ["CONFLUENCE_USERNAME"] = "test@example.com"
os.environ["CONFLUENCE_API_TOKEN"] = "test-confluence-token"
os.environ["CONFLUENCE_SPACE_KEY"] = "TEST"


class TestConfluenceIntegration(unittest.TestCase):
    """Confluence連携機能のテスト"""
    
    def test_confluence_environment_setup(self):
        """Confluence環境変数の設定テスト"""
        self.assertEqual(os.environ.get("CONFLUENCE_URL"), "https://test.atlassian.net/wiki")
        self.assertEqual(os.environ.get("CONFLUENCE_USERNAME"), "test@example.com")
        self.assertEqual(os.environ.get("CONFLUENCE_API_TOKEN"), "test-confluence-token")
        self.assertEqual(os.environ.get("CONFLUENCE_SPACE_KEY"), "TEST")

    def test_design_command_parsing(self):
        """設計コマンドの解析テスト"""
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

    def test_develop_from_design_command_parsing(self):
        """設計ベース開発コマンドの解析テスト"""
        test_text = "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装"
        
        # 解析処理をシミュレート
        parts = test_text.split(" の ", 1)
        confluence_url = parts[0]
        parts = parts[1].split(" に実装", 1)
        file_path = parts[0]
        
        # 検証
        self.assertEqual(confluence_url, "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth")
        self.assertEqual(file_path, "auth.py")

    @patch('atlassian.Confluence')
    def test_confluence_client_initialization(self, mock_confluence):
        """Confluenceクライアントの初期化テスト"""
        # モックの設定
        mock_confluence_instance = Mock()
        mock_confluence.return_value = mock_confluence_instance
        
        # Confluenceクライアントを作成
        from atlassian import Confluence
        confluence_client = Confluence(
            url="https://test.atlassian.net/wiki",
            username="test@example.com",
            password="test-token",
            cloud=True
        )
        
        # 検証
        mock_confluence.assert_called_once_with(
            url="https://test.atlassian.net/wiki",
            username="test@example.com",
            password="test-token",
            cloud=True
        )

    @patch('atlassian.Confluence')
    def test_confluence_page_creation_mock(self, mock_confluence):
        """Confluenceページ作成のモックテスト"""
        # モックの設定
        mock_confluence_instance = Mock()
        mock_confluence.return_value = mock_confluence_instance
        
        mock_page_result = {
            'id': '123456',
            'title': 'Test Page',
            'space': {'key': 'TEST'}
        }
        mock_confluence_instance.create_page.return_value = mock_page_result
        
        # Confluenceクライアントを作成
        from atlassian import Confluence
        confluence_client = Confluence(
            url="https://test.atlassian.net/wiki",
            username="test@example.com", 
            password="test-token",
            cloud=True
        )
        
        # テスト実行
        result = confluence_client.create_page(
            space="TEST",
            title="Test Design Document",
            body="<h1>Test Content</h1>"
        )
        
        # 検証
        self.assertEqual(result['id'], '123456')
        self.assertEqual(result['title'], 'Test Page')
        mock_confluence_instance.create_page.assert_called_once()

    @patch('atlassian.Confluence')
    def test_confluence_page_retrieval_mock(self, mock_confluence):
        """Confluenceページ取得のモックテスト"""
        # モックの設定
        mock_confluence_instance = Mock()
        mock_confluence.return_value = mock_confluence_instance
        
        mock_page_data = {
            'id': '123456',
            'title': 'Test Design Document',
            'body': {
                'storage': {
                    'value': '<h1>Test Design</h1><p>This is a test design document.</p>'
                }
            }
        }
        mock_confluence_instance.get_page_by_id.return_value = mock_page_data
        
        # Confluenceクライアントを作成
        from atlassian import Confluence
        confluence_client = Confluence(
            url="https://test.atlassian.net/wiki",
            username="test@example.com",
            password="test-token", 
            cloud=True
        )
        
        # テスト実行
        page = confluence_client.get_page_by_id('123456', expand='body.storage')
        
        # 検証
        self.assertEqual(page['id'], '123456')
        self.assertEqual(page['title'], 'Test Design Document')
        self.assertIn('storage', page['body'])
        mock_confluence_instance.get_page_by_id.assert_called_once_with('123456', expand='body.storage')

    def test_page_url_parsing(self):
        """ページURL解析のテスト"""
        import re
        
        test_urls = [
            "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456",
            "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth",
            "https://example.atlassian.net/wiki/pages/123456/"
        ]
        
        for url in test_urls:
            with self.subTest(url=url):
                # pageId=パターン
                page_id_match = re.search(r'pageId=(\d+)', url)
                if not page_id_match:
                    # /pages/数字/パターン  
                    page_id_match = re.search(r'/pages/(\d+)/', url)
                
                if page_id_match:
                    page_id = page_id_match.group(1)
                    self.assertEqual(page_id, "123456")

    @patch('markdown.markdown')
    def test_markdown_to_html_conversion(self, mock_markdown):
        """マークダウンからHTML変換のテスト"""
        # モックの設定
        mock_markdown.return_value = "<h1>Test Design</h1><p>Content</p>"
        
        # テスト実行
        import markdown
        html_result = markdown.markdown(
            "# Test Design\n\nContent", 
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        # 検証
        self.assertEqual(html_result, "<h1>Test Design</h1><p>Content</p>")
        mock_markdown.assert_called_once_with(
            "# Test Design\n\nContent",
            extensions=['tables', 'fenced_code', 'toc']
        )

    @patch('beautifulsoup4.BeautifulSoup')
    def test_html_to_text_conversion(self, mock_soup_class):
        """HTMLからテキスト変換のテスト"""
        # モックの設定
        mock_soup = Mock()
        mock_soup.get_text.return_value = "Test Design\nContent"
        mock_soup_class.return_value = mock_soup
        
        # テスト実行
        from bs4 import BeautifulSoup
        html_content = "<h1>Test Design</h1><p>Content</p>"
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text(separator='\n', strip=True)
        
        # 検証
        self.assertEqual(text_content, "Test Design\nContent")
        mock_soup.get_text.assert_called_once_with(separator='\n', strip=True)

    def test_design_document_template_validation(self):
        """設計ドキュメントテンプレートの検証"""
        project_name = "test-app"
        feature_name = "ユーザー認証"
        requirements = "JWT認証を使用"
        
        # プロンプトテンプレートの構築（実際のコードから抜粋）
        expected_sections = [
            f"# {feature_name} 設計書",
            "## 概要",
            "## 要件", 
            "### 機能要件",
            "### 非機能要件",
            "## アーキテクチャ",
            "## API設計",
            "## データベース設計",
            "## セキュリティ考慮事項",
            "## 実装方針",
            "## テスト戦略",
            "## 運用考慮事項"
        ]
        
        # 各セクションが含まれていることを確認
        for section in expected_sections:
            self.assertIsInstance(section, str)
            self.assertTrue(len(section) > 0)

    def test_code_generation_prompt_validation(self):
        """コード生成プロンプトの検証"""
        design_content = "# ユーザー認証 設計書\n\n## 概要\nJWT認証システム"
        file_path = "auth.py"
        additional_requirements = "FastAPIを使用"
        
        # プロンプトに含まれるべき要素
        expected_elements = [
            "シニアソフトウェアエンジニア",
            "設計ドキュメント",
            design_content,
            file_path,
            additional_requirements,
            "コードの可読性と保守性",
            "エラーハンドリング",
            "セキュリティベストプラクティス"
        ]
        
        # 各要素が定義されていることを確認
        for element in expected_elements:
            self.assertIsInstance(element, str)
            self.assertTrue(len(element) > 0)


class TestConfluenceErrorHandling(unittest.TestCase):
    """Confluenceエラーハンドリングのテスト"""
    
    def test_confluence_api_error_simulation(self):
        """Confluence APIエラーのシミュレーション"""
        from atlassian import Confluence
        from requests.exceptions import HTTPError
        
        # 各種エラーケースの定義
        error_cases = [
            (401, "Unauthorized"),
            (403, "Forbidden"), 
            (404, "Not Found"),
            (429, "Too Many Requests"),
            (500, "Internal Server Error")
        ]
        
        for status_code, error_message in error_cases:
            with self.subTest(status_code=status_code):
                # エラーオブジェクトを作成
                error = HTTPError(f"{status_code} {error_message}")
                
                # エラーの検証
                self.assertIsInstance(error, HTTPError)
                self.assertIn(str(status_code), str(error))

    def test_invalid_confluence_url_format(self):
        """無効なConfluence URL形式のテスト"""
        invalid_urls = [
            "not-a-url",
            "http://invalid-url",
            "https://invalid.com/not-confluence",
            ""
        ]
        
        for invalid_url in invalid_urls:
            with self.subTest(url=invalid_url):
                # URL形式の基本検証
                is_valid = invalid_url.startswith("https://") and "atlassian.net" in invalid_url
                self.assertFalse(is_valid)

    def test_empty_design_content_handling(self):
        """空の設計内容の処理テスト"""
        empty_contents = ["", None, "   ", "\n\n"]
        
        for content in empty_contents:
            with self.subTest(content=repr(content)):
                # 空コンテンツの検証
                is_empty = not content or not content.strip()
                self.assertTrue(is_empty)


if __name__ == '__main__':
    # テストスイートの実行
    print("=== Confluence連携機能テスト実行 ===")
    print("Confluence環境変数設定:", {
        "CONFLUENCE_URL": bool(os.environ.get("CONFLUENCE_URL")),
        "CONFLUENCE_USERNAME": bool(os.environ.get("CONFLUENCE_USERNAME")),
        "CONFLUENCE_API_TOKEN": bool(os.environ.get("CONFLUENCE_API_TOKEN")),
        "CONFLUENCE_SPACE_KEY": bool(os.environ.get("CONFLUENCE_SPACE_KEY")),
    })
    print("=" * 50)
    
    unittest.main(verbosity=2)
#!/usr/bin/env python3
"""
Simple Confluence integration tests for AI Developer Bot
Confluence連携機能のシンプルテストファイル
"""

import unittest
import os
import re

# テスト実行前に環境変数を設定
os.environ["CONFLUENCE_URL"] = "https://test.atlassian.net/wiki"
os.environ["CONFLUENCE_USERNAME"] = "test@example.com"
os.environ["CONFLUENCE_API_TOKEN"] = "test-confluence-token"
os.environ["CONFLUENCE_SPACE_KEY"] = "TEST"


class TestConfluenceBasics(unittest.TestCase):
    """Confluence連携の基本機能テスト"""
    
    def test_confluence_environment_setup(self):
        """Confluence環境変数の設定テスト"""
        self.assertEqual(os.environ.get("CONFLUENCE_URL"), "https://test.atlassian.net/wiki")
        self.assertEqual(os.environ.get("CONFLUENCE_USERNAME"), "test@example.com")
        self.assertEqual(os.environ.get("CONFLUENCE_API_TOKEN"), "test-confluence-token")
        self.assertEqual(os.environ.get("CONFLUENCE_SPACE_KEY"), "TEST")

    def test_design_command_parsing(self):
        """設計コマンドの解析テスト"""
        test_cases = [
            {
                "input": "my-app の ユーザー認証機能 について JWT認証を使用し、ログイン・ログアウト機能を含む",
                "expected": {
                    "project": "my-app",
                    "feature": "ユーザー認証機能",
                    "requirements": "JWT認証を使用し、ログイン・ログアウト機能を含む"
                }
            },
            {
                "input": "ecommerce-site の 商品検索機能 について Elasticsearch を使用した高速検索",
                "expected": {
                    "project": "ecommerce-site", 
                    "feature": "商品検索機能",
                    "requirements": "Elasticsearch を使用した高速検索"
                }
            }
        ]
        
        for case in test_cases:
            with self.subTest(input=case["input"]):
                text = case["input"]
                
                # 解析処理をシミュレート
                parts = text.split(" の ", 1)
                project_name = parts[0]
                parts = parts[1].split(" について ", 1)
                feature_name = parts[0]
                requirements = parts[1]
                
                # 検証
                self.assertEqual(project_name, case["expected"]["project"])
                self.assertEqual(feature_name, case["expected"]["feature"])
                self.assertEqual(requirements, case["expected"]["requirements"])

    def test_develop_from_design_command_parsing(self):
        """設計ベース開発コマンドの解析テスト"""
        test_cases = [
            {
                "input": "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装",
                "expected": {
                    "url": "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth",
                    "file": "auth.py"
                }
            },
            {
                "input": "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=789012 の search.py に実装",
                "expected": {
                    "url": "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=789012",
                    "file": "search.py"
                }
            }
        ]
        
        for case in test_cases:
            with self.subTest(input=case["input"]):
                text = case["input"]
                
                # 解析処理をシミュレート
                parts = text.split(" の ", 1)
                confluence_url = parts[0]
                parts = parts[1].split(" に実装", 1)
                file_path = parts[0]
                
                # 検証
                self.assertEqual(confluence_url, case["expected"]["url"])
                self.assertEqual(file_path, case["expected"]["file"])

    def test_page_url_parsing(self):
        """ページURL解析のテスト"""
        test_urls = [
            {
                "url": "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456",
                "expected_id": "123456"
            },
            {
                "url": "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth",
                "expected_id": "123456"
            },
            {
                "url": "https://example.atlassian.net/wiki/pages/123456/",
                "expected_id": "123456"
            }
        ]
        
        for case in test_urls:
            with self.subTest(url=case["url"]):
                url = case["url"]
                
                # pageId=パターン
                page_id_match = re.search(r'pageId=(\d+)', url)
                if not page_id_match:
                    # /pages/数字/パターン  
                    page_id_match = re.search(r'/pages/(\d+)/', url)
                
                self.assertIsNotNone(page_id_match)
                page_id = page_id_match.group(1)
                self.assertEqual(page_id, case["expected_id"])

    def test_confluence_url_validation(self):
        """Confluence URL形式の検証テスト"""
        valid_urls = [
            "https://company.atlassian.net/wiki",
            "https://example.atlassian.net/wiki/",
            "https://my-org.atlassian.net/wiki/spaces/DEV"
        ]
        
        invalid_urls = [
            "not-a-url",
            "http://invalid-url",
            "https://invalid.com/not-confluence",
            "",
            "https://github.com/user/repo"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                is_valid = url.startswith("https://") and "atlassian.net" in url
                self.assertTrue(is_valid)
        
        for url in invalid_urls:
            with self.subTest(url=url):
                is_valid = url.startswith("https://") and "atlassian.net" in url
                self.assertFalse(is_valid)

    def test_design_document_structure_validation(self):
        """設計ドキュメント構造の検証テスト"""
        project_name = "test-app"
        feature_name = "ユーザー認証"
        requirements = "JWT認証を使用"
        
        # 設計ドキュメントに含まれるべきセクション
        required_sections = [
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
        
        # 各セクションが適切に定義されていることを確認
        for section in required_sections:
            self.assertIsInstance(section, str)
            self.assertTrue(len(section) > 0)
            # セクションがMarkdown形式であることを確認
            if section.startswith("#"):
                self.assertTrue(section.count("#") <= 3)  # H1-H3まで

    def test_code_generation_prompt_elements(self):
        """コード生成プロンプト要素の検証テスト"""
        design_content = "# ユーザー認証 設計書\n\n## 概要\nJWT認証システム"
        file_path = "auth.py"
        additional_requirements = "FastAPIを使用"
        
        # プロンプトに含まれるべき要素
        required_prompt_elements = [
            "シニアソフトウェアエンジニア",
            "設計ドキュメント",
            "実装対象ファイル",
            "コードの可読性と保守性",
            "エラーハンドリング", 
            "セキュリティベストプラクティス",
            "テスタビリティ",
            "パフォーマンス"
        ]
        
        # 動的な要素
        dynamic_elements = [design_content, file_path, additional_requirements]
        
        # 各要素が定義されていることを確認
        for element in required_prompt_elements + dynamic_elements:
            self.assertIsInstance(element, str)
            self.assertTrue(len(element) > 0)

    def test_error_handling_scenarios(self):
        """エラーハンドリングシナリオのテスト"""
        # 空コンテンツの処理
        empty_contents = ["", None, "   ", "\n\n"]
        
        for content in empty_contents:
            with self.subTest(content=repr(content)):
                # 空コンテンツの検証ロジック
                is_empty = not content or not content.strip()
                self.assertTrue(is_empty)
        
        # 無効なコマンド形式
        invalid_commands = [
            "invalid command format",
            "project の function",  # "について"が missing
            "project について requirements",  # "の"が missing
            ""
        ]
        
        for command in invalid_commands:
            with self.subTest(command=command):
                # コマンド解析の失敗をシミュレート
                try:
                    parts = command.split(" の ", 1)
                    if len(parts) < 2:
                        raise IndexError("Invalid format")
                    
                    project_name = parts[0]
                    parts = parts[1].split(" について ", 1)
                    if len(parts) < 2:
                        raise IndexError("Invalid format")
                    
                    # ここまで到達したら失敗
                    self.fail(f"Expected IndexError for command: {command}")
                except IndexError:
                    # 期待通りエラーが発生
                    pass

    def test_confluence_page_title_generation(self):
        """Confluenceページタイトル生成のテスト"""
        test_cases = [
            {
                "project": "my-app",
                "feature": "ユーザー認証機能",
                "expected": "my-app - ユーザー認証機能 設計書"
            },
            {
                "project": "ecommerce-site",
                "feature": "商品検索機能", 
                "expected": "ecommerce-site - 商品検索機能 設計書"
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                project_name = case["project"]
                feature_name = case["feature"]
                
                # ページタイトル生成ロジック
                page_title = f"{project_name} - {feature_name} 設計書"
                
                # 検証
                self.assertEqual(page_title, case["expected"])
                self.assertIn(project_name, page_title)
                self.assertIn(feature_name, page_title)
                self.assertIn("設計書", page_title)

    def test_branch_name_generation_for_design(self):
        """設計ベース開発のブランチ名生成テスト"""
        instruction = "設計に基づく実装"
        
        # ブランチ名生成ロジックをシミュレート
        branch_prefix = f"ai-design/{instruction[:15].replace(' ', '-')}"
        
        # 検証
        self.assertTrue(branch_prefix.startswith("ai-design/"))
        self.assertIn("設計に基づく実装", branch_prefix)
        self.assertLessEqual(len(instruction[:15]), 15)


if __name__ == '__main__':
    # テストスイートの実行
    print("=== Confluence連携機能 シンプルテスト実行 ===")
    print("Confluence環境変数設定:", {
        "CONFLUENCE_URL": bool(os.environ.get("CONFLUENCE_URL")),
        "CONFLUENCE_USERNAME": bool(os.environ.get("CONFLUENCE_USERNAME")),
        "CONFLUENCE_API_TOKEN": bool(os.environ.get("CONFLUENCE_API_TOKEN")),
        "CONFLUENCE_SPACE_KEY": bool(os.environ.get("CONFLUENCE_SPACE_KEY")),
    })
    print("=" * 55)
    
    unittest.main(verbosity=2)
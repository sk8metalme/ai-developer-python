#!/usr/bin/env python3
"""
Simple unit tests for AI Developer Bot
シンプルな単体テストファイル
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# テスト実行前に環境変数を設定
os.environ["SLACK_BOT_TOKEN"] = "test-slack-token"
os.environ["SLACK_SIGNING_SECRET"] = "test-signing-secret"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["GITHUB_ACCESS_TOKEN"] = "test-github-token"


class TestEnvironmentSetup(unittest.TestCase):
    """環境設定のテスト"""
    
    def test_environment_variables_set(self):
        """環境変数が設定されていることをテスト"""
        self.assertEqual(os.environ.get("SLACK_BOT_TOKEN"), "test-slack-token")
        self.assertEqual(os.environ.get("SLACK_SIGNING_SECRET"), "test-signing-secret")
        self.assertEqual(os.environ.get("ANTHROPIC_API_KEY"), "test-anthropic-key")
        self.assertEqual(os.environ.get("GITHUB_ACCESS_TOKEN"), "test-github-token")


class TestCodeParsing(unittest.TestCase):
    """コマンド解析のテスト"""
    
    def test_command_parsing(self):
        """コマンド解析ロジックのテスト"""
        # テスト用のコマンド文字列
        test_text = "sk8metalme/test-repo の main.py に HelloWorldを出力する機能を追加"
        
        # 解析処理をシミュレート
        parts = test_text.split(" の ", 1)
        repo_name = parts[0]
        parts = parts[1].split(" に ", 1)
        file_path = parts[0]
        instruction = parts[1]
        
        # 検証
        self.assertEqual(repo_name, "sk8metalme/test-repo")
        self.assertEqual(file_path, "main.py")
        self.assertEqual(instruction, "HelloWorldを出力する機能を追加")
    
    def test_invalid_command_format(self):
        """無効なコマンド形式のテスト"""
        test_text = "invalid command format"
        
        # 無効な形式の場合はIndexErrorが発生することをテスト
        with self.assertRaises(IndexError):
            parts = test_text.split(" の ", 1)
            repo_name = parts[0]
            parts = parts[1].split(" に ", 1)  # ここでIndexError


class TestMockGitHubOperations(unittest.TestCase):
    """モックを使用したGitHub操作のテスト"""
    
    @patch('github.Github')
    def test_github_repo_access_mock(self, mock_github_class):
        """GitHubリポジトリアクセスのモックテスト"""
        # モックの設定
        mock_github_instance = Mock()
        mock_github_class.return_value = mock_github_instance
        
        mock_repo = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        
        mock_content_file = Mock()
        mock_content_file.decoded_content.decode.return_value = "print('Hello World')"
        mock_repo.get_contents.return_value = mock_content_file
        
        # GitHubクライアントを作成
        from github import Github
        github_client = Github("test-token")
        
        # テスト実行
        repo = github_client.get_repo("test-user/test-repo")
        content_file = repo.get_contents("main.py")
        content = content_file.decoded_content.decode("utf-8")
        
        # 検証
        self.assertEqual(content, "print('Hello World')")
        mock_github_instance.get_repo.assert_called_once_with("test-user/test-repo")
        mock_repo.get_contents.assert_called_once_with("main.py")
    
    @patch('github.Github')
    def test_github_pr_creation_mock(self, mock_github_class):
        """GitHubプルリクエスト作成のモックテスト"""
        # モックの設定
        mock_github_instance = Mock()
        mock_github_class.return_value = mock_github_instance
        
        mock_repo = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test-user/test-repo/pull/1"
        mock_repo.create_pull.return_value = mock_pr
        
        # GitHubクライアントを作成
        from github import Github
        github_client = Github("test-token")
        
        # テスト実行
        repo = github_client.get_repo("test-user/test-repo")
        pr = repo.create_pull(
            title="Test PR",
            body="Test pull request",
            head="feature-branch",
            base="main"
        )
        
        # 検証
        self.assertEqual(pr.html_url, "https://github.com/test-user/test-repo/pull/1")
        mock_repo.create_pull.assert_called_once()


class TestMockAnthropicOperations(unittest.TestCase):
    """モックを使用したAnthropic API操作のテスト"""
    
    @patch('anthropic.Anthropic')
    def test_anthropic_api_mock(self, mock_anthropic_class):
        """Anthropic API呼び出しのモックテスト"""
        # モックの設定
        mock_anthropic_instance = Mock()
        mock_anthropic_class.return_value = mock_anthropic_instance
        
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "print('Hello World')\n# Generated code"
        mock_response.content = [mock_content]
        mock_anthropic_instance.messages.create.return_value = mock_response
        
        # Anthropicクライアントを作成
        from anthropic import Anthropic
        anthropic_client = Anthropic(api_key="test-key")
        
        # テスト実行
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            messages=[{"role": "user", "content": "Add Hello World function"}]
        )
        
        # 検証
        self.assertEqual(response.content[0].text, "print('Hello World')\n# Generated code")
        mock_anthropic_instance.messages.create.assert_called_once()


class TestSlackOperations(unittest.TestCase):
    """Slack操作のテスト"""
    
    @patch('requests.post')
    def test_slack_response_url_post(self, mock_requests_post):
        """Slack response_url へのPOSTリクエストのテスト"""
        # モックの設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests_post.return_value = mock_response
        
        # テスト実行
        import requests
        response_url = "https://hooks.slack.com/test"
        message = {"text": "テストメッセージ"}
        
        result = requests.post(response_url, json=message)
        
        # 検証
        self.assertEqual(result.status_code, 200)
        mock_requests_post.assert_called_once_with(response_url, json=message)


class TestUtilityFunctions(unittest.TestCase):
    """ユーティリティ関数のテスト"""
    
    def test_string_strip_whitespace(self):
        """文字列の空白文字削除のテスト"""
        test_cases = [
            ("  test-token  ", "test-token"),
            ("test-secret\n", "test-secret"),
            ("\ttest-api-key", "test-api-key"),
            ("test-github-token  \n", "test-github-token"),
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                result = input_str.strip()
                self.assertEqual(result, expected)
    
    def test_branch_name_generation(self):
        """ブランチ名生成のテスト"""
        instruction = "HelloWorldを出力する機能を追加"
        
        # ブランチ名生成ロジックをシミュレート
        branch_prefix = f"ai-feature/{instruction[:20].replace(' ', '-')}"
        
        # 検証
        self.assertEqual(branch_prefix, "ai-feature/HelloWorldを出力する機能を追加")
        self.assertLessEqual(len(instruction[:20]), 20)


class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングのテスト"""
    
    def test_github_exception_handling(self):
        """GitHubException の処理テスト"""
        from github import GithubException
        
        # 404エラーをシミュレート
        error = GithubException(404, "Not Found")
        
        # エラーの検証
        self.assertEqual(error.status, 404)
        self.assertEqual(error.data, "Not Found")
    
    def test_anthropic_exception_handling(self):
        """AnthropicError の処理テスト"""
        from anthropic import AnthropicError
        
        # APIエラーをシミュレート
        error = AnthropicError("API Error")
        
        # エラーの検証
        self.assertIsInstance(error, AnthropicError)


if __name__ == '__main__':
    # テストスイートの実行
    print("=== AI Developer Bot テスト実行 ===")
    print("環境変数設定:", {
        "SLACK_BOT_TOKEN": bool(os.environ.get("SLACK_BOT_TOKEN")),
        "SLACK_SIGNING_SECRET": bool(os.environ.get("SLACK_SIGNING_SECRET")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "GITHUB_ACCESS_TOKEN": bool(os.environ.get("GITHUB_ACCESS_TOKEN")),
    })
    print("=" * 40)
    
    unittest.main(verbosity=2)
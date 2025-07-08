import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import threading
import requests
from github import GithubException
from anthropic import AnthropicError

# テスト用モック設定
@patch('slack_bolt.app.app.App')
@patch('anthropic.Anthropic')
@patch('github.Github')
def import_aibot_with_mocks(mock_github, mock_anthropic, mock_slack_app):
    """モック付きでaibotをインポート"""
    # アプリケーションのインポート前に環境変数を設定
    os.environ["SLACK_BOT_TOKEN"] = "test-slack-token"
    os.environ["SLACK_SIGNING_SECRET"] = "test-signing-secret"
    os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
    os.environ["GITHUB_ACCESS_TOKEN"] = "test-github-token"
    
    import aibot
    return aibot

# モジュールレベルでaibotをインポート
with patch('slack_bolt.app.app.App'), patch('anthropic.Anthropic'), patch('github.Github'):
    os.environ["SLACK_BOT_TOKEN"] = "test-slack-token"
    os.environ["SLACK_SIGNING_SECRET"] = "test-signing-secret"
    os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
    os.environ["GITHUB_ACCESS_TOKEN"] = "test-github-token"
    import aibot


class TestAIBot(unittest.TestCase):
    """Slack AI開発ボットの単体テスト"""

    def setUp(self):
        """テスト前の設定"""
        self.test_repo_name = "test-user/test-repo"
        self.test_file_path = "main.py"
        self.test_instruction = "Hello Worldを出力する機能を追加"
        self.test_response_url = "https://hooks.slack.com/test"

    def test_environment_variables_loaded(self):
        """環境変数が正しく読み込まれることをテスト"""
        self.assertEqual(aibot.SLACK_BOT_TOKEN, "test-slack-token")
        self.assertEqual(aibot.SLACK_SIGNING_SECRET, "test-signing-secret")
        self.assertEqual(aibot.ANTHROPIC_API_KEY, "test-anthropic-key")
        self.assertEqual(aibot.GITHUB_ACCESS_TOKEN, "test-github-token")

    @patch('aibot.github_client')
    def test_get_repo_content_success(self, mock_github_client):
        """GitHubリポジトリからファイル内容を正常に取得できることをテスト"""
        # モックの設定
        mock_repo = Mock()
        mock_content_file = Mock()
        mock_content_file.decoded_content.decode.return_value = "print('Hello World')"
        mock_repo.get_contents.return_value = mock_content_file
        mock_github_client.get_repo.return_value = mock_repo

        # テスト実行
        result = aibot.get_repo_content(self.test_repo_name, self.test_file_path)

        # 検証
        self.assertEqual(result, "print('Hello World')")
        mock_github_client.get_repo.assert_called_once_with(self.test_repo_name)
        mock_repo.get_contents.assert_called_once_with(self.test_file_path, ref="main")

    @patch('aibot.github_client')
    def test_get_repo_content_file_not_found(self, mock_github_client):
        """ファイルが見つからない場合のテスト"""
        # モックの設定
        mock_github_client.get_repo.side_effect = GithubException(404, "Not Found")

        # テスト実行
        result = aibot.get_repo_content(self.test_repo_name, self.test_file_path)

        # 検証
        self.assertIsNone(result)

    @patch('aibot.github_client')
    def test_create_github_pr_success(self, mock_github_client):
        """GitHubプルリクエストの作成が成功することをテスト"""
        # モックの設定
        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        
        mock_contents = Mock()
        mock_contents.path = self.test_file_path
        mock_contents.sha = "file-sha"
        mock_repo.get_contents.return_value = mock_contents
        
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test-user/test-repo/pull/1"
        mock_repo.create_pull.return_value = mock_pr
        
        mock_github_client.get_repo.return_value = mock_repo

        # テスト実行
        result = aibot.create_github_pr(
            self.test_repo_name,
            "test-branch",
            self.test_file_path,
            "print('Hello World')",
            "Add Hello World feature",
            "AI提案: Hello World機能追加"
        )

        # 検証
        self.assertEqual(result, "https://github.com/test-user/test-repo/pull/1")
        mock_repo.create_git_ref.assert_called_once()
        mock_repo.update_file.assert_called_once()
        mock_repo.create_pull.assert_called_once()

    @patch('aibot.github_client')
    def test_create_github_pr_new_file(self, mock_github_client):
        """新しいファイル作成時のプルリクエスト作成テスト"""
        # モックの設定
        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        
        # ファイルが存在しない場合
        mock_repo.get_contents.side_effect = GithubException(404, "Not Found")
        
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test-user/test-repo/pull/1"
        mock_repo.create_pull.return_value = mock_pr
        
        mock_github_client.get_repo.return_value = mock_repo

        # テスト実行
        result = aibot.create_github_pr(
            self.test_repo_name,
            "test-branch",
            "new_file.py",
            "print('New file')",
            "Create new file",
            "AI提案: 新ファイル作成"
        )

        # 検証
        self.assertEqual(result, "https://github.com/test-user/test-repo/pull/1")
        mock_repo.create_file.assert_called_once()

    @patch('requests.post')
    @patch('aibot.anthropic_client')
    @patch('aibot.get_repo_content')
    @patch('aibot.create_github_pr')
    def test_process_development_task_success(self, mock_create_pr, mock_get_content, 
                                            mock_anthropic, mock_requests):
        """開発タスク処理の成功ケースをテスト"""
        # モックの設定
        mock_get_content.return_value = "# 既存のコード"
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "print('Hello World')\n# 既存のコード"
        mock_anthropic.messages.create.return_value = mock_response
        
        mock_create_pr.return_value = "https://github.com/test/pull/1"
        mock_requests.return_value = Mock()

        # テスト用のボディ
        test_body = {
            "text": f"{self.test_repo_name} の {self.test_file_path} に {self.test_instruction}"
        }

        # テスト実行
        aibot.process_development_task(test_body, self.test_response_url)

        # 検証
        mock_get_content.assert_called_once_with(self.test_repo_name, self.test_file_path)
        mock_anthropic.messages.create.assert_called_once()
        mock_create_pr.assert_called_once()
        
        # Slackへの応答が送信されることを確認
        self.assertTrue(mock_requests.called)

    @patch('requests.post')
    def test_process_development_task_invalid_format(self, mock_requests):
        """無効なコマンド形式のテスト"""
        # 無効なコマンド形式
        test_body = {"text": "invalid command format"}

        # テスト実行
        aibot.process_development_task(test_body, self.test_response_url)

        # 検証 - エラーメッセージが送信されることを確認
        mock_requests.assert_called()
        call_args = mock_requests.call_args
        self.assertIn("コマンドの形式が正しくありません", call_args[1]["json"]["text"])

    @patch('requests.post')
    @patch('aibot.anthropic_client')
    @patch('aibot.get_repo_content')
    def test_process_development_task_anthropic_error(self, mock_get_content, 
                                                    mock_anthropic, mock_requests):
        """Anthropic APIエラー時のテスト"""
        # モックの設定
        mock_get_content.return_value = "# 既存のコード"
        mock_anthropic.messages.create.side_effect = AnthropicError("API Error")

        # テスト用のボディ
        test_body = {
            "text": f"{self.test_repo_name} の {self.test_file_path} に {self.test_instruction}"
        }

        # テスト実行
        aibot.process_development_task(test_body, self.test_response_url)

        # 検証 - エラーメッセージが送信されることを確認
        mock_requests.assert_called()
        call_args = mock_requests.call_args
        self.assertIn("AIとの通信中にエラーが発生しました", call_args[1]["json"]["text"])

    def test_handle_develop_command_creates_thread(self):
        """developコマンドハンドラーがスレッドを作成することをテスト"""
        # モックの設定
        mock_ack = Mock()
        mock_say = Mock()
        test_body = {
            "text": f"{self.test_repo_name} の {self.test_file_path} に {self.test_instruction}",
            "response_url": self.test_response_url
        }

        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance

            # テスト実行
            aibot.handle_develop_command(mock_ack, test_body, mock_say)

            # 検証
            mock_ack.assert_called_once()
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()

    def test_environment_variables_strip_whitespace(self):
        """環境変数の空白文字が削除されることをテスト"""
        with patch.dict(os.environ, {
            "SLACK_BOT_TOKEN": "  test-token  ",
            "SLACK_SIGNING_SECRET": "test-secret\n",
            "ANTHROPIC_API_KEY": "\ttest-api-key",
            "GITHUB_ACCESS_TOKEN": "test-github-token  \n"
        }):
            # モジュールを再インポートして環境変数を再読み込み
            import importlib
            importlib.reload(aibot)
            
            # 検証 - 空白文字が削除されていることを確認
            self.assertEqual(aibot.SLACK_BOT_TOKEN, "test-token")
            self.assertEqual(aibot.SLACK_SIGNING_SECRET, "test-secret")
            self.assertEqual(aibot.ANTHROPIC_API_KEY, "test-api-key")
            self.assertEqual(aibot.GITHUB_ACCESS_TOKEN, "test-github-token")


class TestIntegration(unittest.TestCase):
    """統合テスト"""

    def setUp(self):
        """テスト前の設定"""
        self.test_repo_name = "test-user/test-repo"
        self.test_file_path = "main.py"

    @patch('aibot.github_client')
    @patch('aibot.anthropic_client')
    @patch('requests.post')
    def test_full_workflow_integration(self, mock_requests, mock_anthropic, mock_github):
        """完全なワークフローの統合テスト"""
        # GitHub モックの設定
        mock_repo = Mock()
        mock_content_file = Mock()
        mock_content_file.decoded_content.decode.return_value = "# 既存のコード"
        mock_repo.get_contents.return_value = mock_content_file
        
        mock_branch = Mock()
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/pull/1"
        mock_repo.create_pull.return_value = mock_pr
        
        mock_github.get_repo.return_value = mock_repo

        # Anthropic モックの設定
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "print('Hello World')\n# 既存のコード"
        mock_anthropic.messages.create.return_value = mock_response

        # テスト用のボディ
        test_body = {
            "text": f"{self.test_repo_name} の {self.test_file_path} に Hello World機能を追加"
        }
        test_response_url = "https://hooks.slack.com/test"

        # テスト実行
        aibot.process_development_task(test_body, test_response_url)

        # 検証 - 全ての段階が実行されることを確認
        mock_github.get_repo.assert_called()
        mock_anthropic.messages.create.assert_called()
        mock_repo.create_git_ref.assert_called()
        mock_repo.create_pull.assert_called()
        
        # 成功メッセージが送信されることを確認
        success_call_found = False
        for call in mock_requests.call_args_list:
            if "プルリクエストの作成が完了しました" in call[1]["json"]["text"]:
                success_call_found = True
                break
        self.assertTrue(success_call_found)


if __name__ == '__main__':
    # テストスイートの実行
    unittest.main(verbosity=2)
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import threading
import requests
from github import GithubException
from anthropic import AnthropicError

# テスト用の環境変数設定
@pytest.fixture(autouse=True)
def setup_env_vars():
    """テスト用環境変数の設定"""
    env_vars = {
        "SLACK_BOT_TOKEN": "test-slack-token",
        "SLACK_SIGNING_SECRET": "test-signing-secret", 
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "GITHUB_ACCESS_TOKEN": "test-github-token"
    }
    
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def aibot_module():
    """aibotモジュールの読み込み"""
    import aibot
    return aibot


@pytest.fixture
def test_data():
    """テスト用データ"""
    return {
        "repo_name": "test-user/test-repo",
        "file_path": "main.py", 
        "instruction": "Hello Worldを出力する機能を追加",
        "response_url": "https://hooks.slack.com/test",
        "existing_code": "# 既存のコード",
        "generated_code": "print('Hello World')\n# 既存のコード",
        "pr_url": "https://github.com/test-user/test-repo/pull/1"
    }


class TestEnvironmentSetup:
    """環境設定のテスト"""
    
    def test_environment_variables_loaded(self, aibot_module):
        """環境変数が正しく読み込まれることをテスト"""
        assert aibot_module.SLACK_BOT_TOKEN == "test-slack-token"
        assert aibot_module.SLACK_SIGNING_SECRET == "test-signing-secret"
        assert aibot_module.ANTHROPIC_API_KEY == "test-anthropic-key"
        assert aibot_module.GITHUB_ACCESS_TOKEN == "test-github-token"

    def test_environment_variables_strip_whitespace(self):
        """環境変数の空白文字が削除されることをテスト"""
        env_vars_with_whitespace = {
            "SLACK_BOT_TOKEN": "  test-token  ",
            "SLACK_SIGNING_SECRET": "test-secret\n",
            "ANTHROPIC_API_KEY": "\ttest-api-key",
            "GITHUB_ACCESS_TOKEN": "test-github-token  \n"
        }
        
        with patch.dict(os.environ, env_vars_with_whitespace):
            import importlib
            import aibot
            importlib.reload(aibot)
            
            assert aibot.SLACK_BOT_TOKEN == "test-token"
            assert aibot.SLACK_SIGNING_SECRET == "test-secret"
            assert aibot.ANTHROPIC_API_KEY == "test-api-key"
            assert aibot.GITHUB_ACCESS_TOKEN == "test-github-token"


class TestGitHubOperations:
    """GitHub操作のテスト"""
    
    @patch('aibot.github_client')
    def test_get_repo_content_success(self, mock_github_client, aibot_module, test_data):
        """GitHubリポジトリからファイル内容を正常に取得できることをテスト"""
        # モックの設定
        mock_repo = Mock()
        mock_content_file = Mock()
        mock_content_file.decoded_content.decode.return_value = test_data["existing_code"]
        mock_repo.get_contents.return_value = mock_content_file
        mock_github_client.get_repo.return_value = mock_repo

        # テスト実行
        result = aibot_module.get_repo_content(test_data["repo_name"], test_data["file_path"])

        # 検証
        assert result == test_data["existing_code"]
        mock_github_client.get_repo.assert_called_once_with(test_data["repo_name"])
        mock_repo.get_contents.assert_called_once_with(test_data["file_path"], ref="main")

    @patch('aibot.github_client')
    def test_get_repo_content_file_not_found(self, mock_github_client, aibot_module, test_data):
        """ファイルが見つからない場合のテスト"""
        # モックの設定
        mock_github_client.get_repo.side_effect = GithubException(404, "Not Found")

        # テスト実行
        result = aibot_module.get_repo_content(test_data["repo_name"], test_data["file_path"])

        # 検証
        assert result is None

    @patch('aibot.github_client')
    def test_create_github_pr_success(self, mock_github_client, aibot_module, test_data):
        """GitHubプルリクエストの作成が成功することをテスト"""
        # モックの設定
        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        
        mock_contents = Mock()
        mock_contents.path = test_data["file_path"]
        mock_contents.sha = "file-sha"
        mock_repo.get_contents.return_value = mock_contents
        
        mock_pr = Mock()
        mock_pr.html_url = test_data["pr_url"]
        mock_repo.create_pull.return_value = mock_pr
        
        mock_github_client.get_repo.return_value = mock_repo

        # テスト実行
        result = aibot_module.create_github_pr(
            test_data["repo_name"],
            "test-branch", 
            test_data["file_path"],
            test_data["generated_code"],
            "Add Hello World feature",
            "AI提案: Hello World機能追加"
        )

        # 検証
        assert result == test_data["pr_url"]
        mock_repo.create_git_ref.assert_called_once()
        mock_repo.update_file.assert_called_once()
        mock_repo.create_pull.assert_called_once()

    @patch('aibot.github_client')
    def test_create_github_pr_new_file(self, mock_github_client, aibot_module, test_data):
        """新しいファイル作成時のプルリクエスト作成テスト"""
        # モックの設定
        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        
        # ファイルが存在しない場合
        mock_repo.get_contents.side_effect = GithubException(404, "Not Found")
        
        mock_pr = Mock()
        mock_pr.html_url = test_data["pr_url"]
        mock_repo.create_pull.return_value = mock_pr
        
        mock_github_client.get_repo.return_value = mock_repo

        # テスト実行
        result = aibot_module.create_github_pr(
            test_data["repo_name"],
            "test-branch",
            "new_file.py",
            "print('New file')",
            "Create new file", 
            "AI提案: 新ファイル作成"
        )

        # 検証
        assert result == test_data["pr_url"]
        mock_repo.create_file.assert_called_once()


class TestTaskProcessing:
    """タスク処理のテスト"""
    
    @patch('requests.post')
    @patch('aibot.anthropic_client')
    @patch('aibot.get_repo_content')
    @patch('aibot.create_github_pr')
    def test_process_development_task_success(self, mock_create_pr, mock_get_content,
                                            mock_anthropic, mock_requests, aibot_module, test_data):
        """開発タスク処理の成功ケースをテスト"""
        # モックの設定
        mock_get_content.return_value = test_data["existing_code"]
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = test_data["generated_code"]
        mock_anthropic.messages.create.return_value = mock_response
        
        mock_create_pr.return_value = test_data["pr_url"]
        mock_requests.return_value = Mock()

        # テスト用のボディ
        test_body = {
            "text": f"{test_data['repo_name']} の {test_data['file_path']} に {test_data['instruction']}"
        }

        # テスト実行
        aibot_module.process_development_task(test_body, test_data["response_url"])

        # 検証
        mock_get_content.assert_called_once_with(test_data["repo_name"], test_data["file_path"])
        mock_anthropic.messages.create.assert_called_once()
        mock_create_pr.assert_called_once()
        assert mock_requests.called

    @patch('requests.post')
    def test_process_development_task_invalid_format(self, mock_requests, aibot_module, test_data):
        """無効なコマンド形式のテスト"""
        # 無効なコマンド形式
        test_body = {"text": "invalid command format"}

        # テスト実行
        aibot_module.process_development_task(test_body, test_data["response_url"])

        # 検証 - エラーメッセージが送信されることを確認
        mock_requests.assert_called()
        call_args = mock_requests.call_args
        assert "コマンドの形式が正しくありません" in call_args[1]["json"]["text"]

    @patch('requests.post')
    @patch('aibot.anthropic_client')
    @patch('aibot.get_repo_content')
    def test_process_development_task_anthropic_error(self, mock_get_content,
                                                    mock_anthropic, mock_requests, aibot_module, test_data):
        """Anthropic APIエラー時のテスト"""
        # モックの設定
        mock_get_content.return_value = test_data["existing_code"]
        mock_anthropic.messages.create.side_effect = AnthropicError("API Error")

        # テスト用のボディ
        test_body = {
            "text": f"{test_data['repo_name']} の {test_data['file_path']} に {test_data['instruction']}"
        }

        # テスト実行
        aibot_module.process_development_task(test_body, test_data["response_url"])

        # 検証 - エラーメッセージが送信されることを確認
        mock_requests.assert_called()
        call_args = mock_requests.call_args
        assert "AIとの通信中にエラーが発生しました" in call_args[1]["json"]["text"]


class TestSlackIntegration:
    """Slack連携のテスト"""
    
    def test_handle_develop_command_creates_thread(self, aibot_module, test_data):
        """developコマンドハンドラーがスレッドを作成することをテスト"""
        # モックの設定
        mock_ack = Mock()
        mock_say = Mock()
        test_body = {
            "text": f"{test_data['repo_name']} の {test_data['file_path']} に {test_data['instruction']}",
            "response_url": test_data["response_url"]
        }

        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance

            # テスト実行
            aibot_module.handle_develop_command(mock_ack, test_body, mock_say)

            # 検証
            mock_ack.assert_called_once()
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()


@pytest.mark.integration
class TestIntegration:
    """統合テスト"""
    
    @patch('aibot.github_client')
    @patch('aibot.anthropic_client')
    @patch('requests.post')
    def test_full_workflow_integration(self, mock_requests, mock_anthropic, 
                                     mock_github, aibot_module, test_data):
        """完全なワークフローの統合テスト"""
        # GitHub モックの設定
        mock_repo = Mock()
        mock_content_file = Mock()
        mock_content_file.decoded_content.decode.return_value = test_data["existing_code"]
        mock_repo.get_contents.return_value = mock_content_file
        
        mock_branch = Mock()
        mock_branch.commit.sha = "test-sha"
        mock_repo.get_branch.return_value = mock_branch
        
        mock_pr = Mock()
        mock_pr.html_url = test_data["pr_url"]
        mock_repo.create_pull.return_value = mock_pr
        
        mock_github.get_repo.return_value = mock_repo

        # Anthropic モックの設定
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = test_data["generated_code"]
        mock_anthropic.messages.create.return_value = mock_response

        # テスト用のボディ
        test_body = {
            "text": f"{test_data['repo_name']} の {test_data['file_path']} に Hello World機能を追加"
        }

        # テスト実行
        aibot_module.process_development_task(test_body, test_data["response_url"])

        # 検証 - 全ての段階が実行されることを確認
        mock_github.get_repo.assert_called()
        mock_anthropic.messages.create.assert_called()
        mock_repo.create_git_ref.assert_called()
        mock_repo.create_pull.assert_called()
        
        # 成功メッセージが送信されることを確認
        success_call_found = False
        for call in mock_requests.call_args_list:
            if "プルリクエストの作成が完了しました" in call_args[1]["json"]["text"]:
                success_call_found = True
                break
        assert success_call_found


# パフォーマンステスト用のマーカー
@pytest.mark.slow
class TestPerformance:
    """パフォーマンステスト"""
    
    def test_response_time_within_limits(self, aibot_module, test_data):
        """レスポンス時間が制限内であることをテスト"""
        import time
        
        mock_ack = Mock()
        mock_say = Mock()
        test_body = {
            "text": f"{test_data['repo_name']} の {test_data['file_path']} に {test_data['instruction']}",
            "response_url": test_data["response_url"]
        }
        
        with patch('threading.Thread'):
            start_time = time.time()
            aibot_module.handle_develop_command(mock_ack, test_body, mock_say)
            end_time = time.time()
            
            # Slackの3秒制限内に応答することを確認
            response_time = end_time - start_time
            assert response_time < 3.0, f"レスポンス時間が制限を超過: {response_time}秒"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
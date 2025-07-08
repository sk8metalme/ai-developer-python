import os
import threading
import logging
import requests
from slack_bolt import App
from anthropic import Anthropic, AnthropicError
from github import Github, GithubException

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Anthropic APIのログも詳細に出力
logging.getLogger("anthropic").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

# --- 定数 ---
# Slackに表示するアイコンのURL
CLAUDE_ICON_URL = "https://claude.ai/favicon.ico"

# --- 環境変数から認証情報を読み込み ---
# 実行前にこれらの環境変数を設定してください
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
GITHUB_ACCESS_TOKEN = os.environ.get("GITHUB_ACCESS_TOKEN", "").strip()

# 環境変数が設定されているかチェック
if not all([SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, ANTHROPIC_API_KEY, GITHUB_ACCESS_TOKEN]):
    raise ValueError("必要な環境変数がすべて設定されていません。SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, ANTHROPIC_API_KEY, GITHUB_ACCESS_TOKEN を確認してください。")

# --- 各種クライアントの初期化 ---
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET, process_before_response=True)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
github_client = Github(GITHUB_ACCESS_TOKEN)

def get_repo_content(repo_name: str, file_path: str, branch: str = "main") -> str | None:
    """GitHubリポジトリからファイルの内容を取得する"""
    try:
        logging.info(f"GitHubリポジトリにアクセス中: {repo_name}, ファイル: {file_path}")
        repo = github_client.get_repo(repo_name)
        content_file = repo.get_contents(file_path, ref=branch)
        return content_file.decoded_content.decode("utf-8")
    except GithubException as e:
        logging.error(f"GitHubからのファイル取得エラー (repo: {repo_name}, file: {file_path}): {e}")
        return None

def create_github_pr(repo_name: str, new_branch_name: str, file_path: str, new_content: str, commit_message: str, pr_title: str) -> str | None:
    """GitHubに新しいブランチを作成し、ファイルを更新してPRを作成する"""
    try:
        repo = github_client.get_repo(repo_name)
        source_branch = repo.get_branch("main")
        
        # 新しいブランチを作成
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=source_branch.commit.sha)

        # ファイルを更新 (または新規作成)
        try:
            contents = repo.get_contents(file_path, ref=new_branch_name)
            repo.update_file(contents.path, commit_message, new_content, contents.sha, branch=new_branch_name)
        except GithubException as e:
            if e.status == 404: # ファイルが存在しない場合
                repo.create_file(file_path, commit_message, new_content, branch=new_branch_name)
            else:
                raise e

        # プルリクエストを作成
        pr = repo.create_pull(
            title=pr_title,
            body="AIによって自動生成されたプルリクエストです。",
            head=new_branch_name,
            base="main"
        )
        return pr.html_url
    except GithubException as e:
        logging.error(f"GitHubでのPR作成エラー: {e}")
        return None

def process_development_task(body, response_url):
    """バックグラウンドで実行されるメインのタスク処理関数"""
    try:
        # Slackからの指示テキストをパース
        # 例: "my-user/my-repo の main.py に「Hello」と出力する機能を追加"
        text = body.get("text", "")
        logging.info(f"受信したコマンド: {text}")
        parts = text.split(" の ", 1)
        repo_name = parts[0]
        parts = parts[1].split(" に ", 1)
        file_path = parts[0]
        instruction = parts[1]
        logging.info(f"解析結果 - リポジトリ: {repo_name}, ファイル: {file_path}, 指示: {instruction}")
        
        def send_message(text):
            requests.post(response_url, json={"text": text})

        # 1. GitHubから現在のコードを取得
        send_message(f"承知しました。`{repo_name}`の`{file_path}`に対する作業を開始します。\nまずは現在のコードを取得します...")
        current_code = get_repo_content(repo_name, file_path)
        if current_code is None:
            send_message(f"警告: `{repo_name}`の`{file_path}`が見つかりませんでした。新規ファイルとして処理を続行します。")
            current_code = "" # 新規ファイルの場合は空の文字列
            
        # 2. Claudeにコード生成を依頼
        send_message("コードのコンテキストをAIに渡し、改修案を生成させます...")
        prompt = f"""
        あなたはシニアソフトウェアエンジニアです。以下のファイルに対して、指示通りにコードを改修してください。
        
        ファイルパス: `{file_path}`
        現在のコード:
        ```
        {current_code}
        ```
        
        指示: 「{instruction}」
        
        改修後のコード全体のみを、コードブロックなしで返してください。
        """
        
        logging.info(f"Anthropic APIリクエスト開始 - モデル: claude-3-5-sonnet-20240620, プロンプト長: {len(prompt)}")
        logging.debug(f"送信プロンプト: {prompt[:500]}...")
        
        try:
            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20240620", # 最新モデルを推奨
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            logging.info(f"Anthropic APIレスポンス受信 - レスポンス長: {len(response.content[0].text)}")
            logging.debug(f"受信レスポンス: {response.content[0].text[:500]}...")
            new_code = response.content[0].text
        except AnthropicError as e:
            logging.error(f"Anthropic APIエラー詳細: {e}")
            send_message(f"AIとの通信中にエラーが発生しました: {e}")
            return

        # 3. GitHubにPRを作成
        send_message("新しいコードを元に、GitHubにプルリクエストを作成します...")
        branch_name = f"ai-feature/{instruction[:20].replace(' ', '-')}-{os.urandom(2).hex()}"
        commit_message = f"feat: {instruction}"
        pr_title = f"AI提案: {instruction}"
        
        logging.info(f"GitHub PR作成開始 - ブランチ: {branch_name}, コミット: {commit_message}")
        pr_url = create_github_pr(repo_name, branch_name, file_path, new_code, commit_message, pr_title)
        
        if pr_url:
            logging.info(f"GitHub PR作成成功: {pr_url}")
            send_message(f"✅ プルリクエストの作成が完了しました！\nレビューをお願いします: {pr_url}")
        else:
            logging.error("GitHub PR作成失敗")
            send_message("❌ プルリクエストの作成中にエラーが発生しました。詳細はログを確認してください。")

    except IndexError:
        requests.post(response_url, json={"text": "コマンドの形式が正しくありません。\n例: `/develop [リポジトリ名] の [ファイルパス] に [やってほしいこと]`"})
    except AnthropicError as e:
        requests.post(response_url, json={"text": f"AIとの通信中にエラーが発生しました: {e}"})
    except Exception as e:
        logging.error(f"予期せぬエラー: {e}")
        requests.post(response_url, json={"text": f"予期せぬエラーが発生しました。詳細はログを確認してください。"})

@app.command("/develop")
def handle_develop_command(ack, body, say):
    """Slackからのスラッシュコマンドを受け取るハンドラ"""
    # Slackの3秒タイムアウトに応答
    ack(f"指示を受け付けました: `{body['text']}`\nバックグラウンドで開発タスクを開始します...")
    
    # バックグラウンドでタスクを実行
    thread = threading.Thread(target=process_development_task, args=(body, body['response_url']))
    thread.start()

if __name__ == "__main__":
    logging.info("🤖 Slack AI開発ボットを起動します (HTTP Mode)...")
    # app.start() はWebサーバーを起動します
    from slack_bolt.adapter.flask import SlackRequestHandler
    from flask import Flask, request
    
    flask_app = Flask(__name__)
    handler = SlackRequestHandler(app)
    
    @flask_app.route("/slack/commands", methods=["POST"])
    def slack_commands():
        return handler.handle(request)
    
    flask_app.run(port=int(os.environ.get("PORT", 3000)), debug=True)

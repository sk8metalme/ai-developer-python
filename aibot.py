import os
import threading
import logging
import requests
import re
import markdown
import asyncio
from typing import Optional, Union
from slack_bolt import App
from anthropic import Anthropic, AnthropicError
from github import Github, GithubException
from atlassian import Confluence
from bs4 import BeautifulSoup
from google.cloud import secretmanager

# 共通の非同期実行関数
def run_async_safely(coro):
    """非同期コルーチンを安全に実行する関数"""
    def run_in_thread():
        try:
            # 新しいイベントループを作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            logging.error(f"非同期タスク実行エラー: {e}")
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

# Atlassian MCP Client のインポート
try:
    from atlassian_mcp_integration import (
        create_confluence_page_mcp,
        get_confluence_page_mcp,
        search_confluence_pages_mcp,
        generate_design_document_mcp
    )
    MCP_AVAILABLE = True
    logging.info("Atlassian MCP Client が利用可能です")
except ImportError as e:
    MCP_AVAILABLE = False
    logging.warning(f"Atlassian MCP Client のインポートに失敗しました: {e}")

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Anthropic APIのログも詳細に出力
logging.getLogger("anthropic").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

# --- 定数 ---
# Slackに表示するアイコンのURL
CLAUDE_ICON_URL = "https://claude.ai/favicon.ico"

# --- Secret Manager クライアント ---
def get_secret_value(secret_name: str, project_id: Optional[str] = None) -> str:
    """Google Cloud Secret Managerからシークレット値を取得する"""
    try:
        if project_id is None:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        
        client = secretmanager.SecretManagerServiceClient()
        
        if not project_id:
            # プロジェクトIDが設定されていない場合、メタデータサービスから自動検出を試行
            try:
                import google.auth
                _, project_id = google.auth.default()
                logging.warning(f"GOOGLE_CLOUD_PROJECT not set, auto-detected project: {project_id} for {secret_name}")
            except Exception:
                logging.error(f"Could not auto-detect project for {secret_name}, falling back to environment variable")
                return os.environ.get(secret_name, "").strip()
        
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8").strip()
        logging.info(f"Successfully retrieved secret: {secret_name}")
        return secret_value
    except Exception as e:
        logging.warning(f"Failed to retrieve secret {secret_name} from Secret Manager: {e}")
        # Secret Managerから取得できない場合は環境変数にフォールバック
        return os.environ.get(secret_name, "").strip()

# --- 環境変数・シークレットから認証情報を読み込み ---
# Google Cloud環境ではSecret Managerから、ローカル環境では環境変数から取得
import concurrent.futures
import time

def load_secrets_parallel():
    """並行処理でシークレットを読み込み"""
    secrets = {}
    secret_names = [
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "ANTHROPIC_API_KEY", 
        "GITHUB_ACCESS_TOKEN",
        "CONFLUENCE_URL",
        "CONFLUENCE_USERNAME",
        "CONFLUENCE_API_TOKEN",
        "CONFLUENCE_SPACE_KEY"
    ]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_secret = {executor.submit(get_secret_value, secret_name): secret_name for secret_name in secret_names}
        
        for future in concurrent.futures.as_completed(future_to_secret):
            secret_name = future_to_secret[future]
            try:
                secrets[secret_name] = future.result()
                logging.info(f"Successfully retrieved secret: {secret_name}")
            except Exception as e:
                logging.error(f"Failed to retrieve secret {secret_name}: {e}")
                secrets[secret_name] = ""
    
    return secrets

logging.info("Loading secrets in parallel...")
start_time = time.time()
secrets = load_secrets_parallel()
end_time = time.time()
logging.info(f"Secrets loaded in {end_time - start_time:.2f} seconds")

SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = secrets["SLACK_APP_TOKEN"]  # Socket Mode用
ANTHROPIC_API_KEY = secrets["ANTHROPIC_API_KEY"]
GITHUB_ACCESS_TOKEN = secrets["GITHUB_ACCESS_TOKEN"]

# Confluence設定（オプショナル）
CONFLUENCE_URL = secrets["CONFLUENCE_URL"]
CONFLUENCE_USERNAME = secrets["CONFLUENCE_USERNAME"]
CONFLUENCE_API_TOKEN = secrets["CONFLUENCE_API_TOKEN"]
CONFLUENCE_SPACE_KEY = secrets["CONFLUENCE_SPACE_KEY"] or "DEV"

# 基本環境変数が設定されているかチェック（ビルド時のテストではスキップ）
if not os.environ.get("GITHUB_ACTIONS"):
    missing_vars = []
    if not SLACK_BOT_TOKEN:
        missing_vars.append("SLACK_BOT_TOKEN")
    if not SLACK_APP_TOKEN:
        missing_vars.append("SLACK_APP_TOKEN")
    if not ANTHROPIC_API_KEY:
        missing_vars.append("ANTHROPIC_API_KEY")
    if not GITHUB_ACCESS_TOKEN:
        missing_vars.append("GITHUB_ACCESS_TOKEN")
    
    if missing_vars:
        logging.error(f"環境変数の詳細状況:")
        logging.error(f"  SLACK_BOT_TOKEN: {'設定済み' if SLACK_BOT_TOKEN else '未設定'}")
        logging.error(f"  SLACK_APP_TOKEN: {'設定済み' if SLACK_APP_TOKEN else '未設定'}")
        logging.error(f"  ANTHROPIC_API_KEY: {'設定済み' if ANTHROPIC_API_KEY else '未設定'}")
        logging.error(f"  GITHUB_ACCESS_TOKEN: {'設定済み' if GITHUB_ACCESS_TOKEN else '未設定'}")
        logging.error(f"  GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT', '未設定')}")
        raise ValueError(f"必要な環境変数が設定されていません: {', '.join(missing_vars)}")

# Confluence設定のチェック
CONFLUENCE_ENABLED = all([CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN])
if CONFLUENCE_ENABLED:
    logging.info("Confluence連携が有効になりました")
else:
    logging.warning("Confluence環境変数が不完全です。Confluence機能は無効になります。")

# --- 各種クライアントの初期化 ---
# GitHub Actionsでのビルド時はダミートークンで初期化
if os.environ.get("GITHUB_ACTIONS"):
    # GitHub Actions実行時はダミー値で初期化（認証テスト無効）
    dummy_token = "x" + "oxb-" + "dummy-" + "build-" + "token"
    app = App(token=dummy_token, process_before_response=True, 
              token_verification_enabled=False)
    anthropic_client = None
    github_client = None
else:
    app = App(token=SLACK_BOT_TOKEN, process_before_response=True)
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    github_client = Github(GITHUB_ACCESS_TOKEN)

# Confluenceクライアントの初期化（有効な場合のみ）
confluence_client = None
if CONFLUENCE_ENABLED and not os.environ.get("GITHUB_ACTIONS"):
    try:
        confluence_client = Confluence(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            password=CONFLUENCE_API_TOKEN,
            cloud=True
        )
        logging.info("Confluenceクライアントの初期化が完了しました")
    except Exception as e:
        logging.error(f"Confluenceクライアントの初期化に失敗しました: {e}")
        CONFLUENCE_ENABLED = False

def get_repo_content(repo_name: str, file_path: str, branch: str = "main") -> Optional[str]:
    """GitHubリポジトリからファイルの内容を取得する"""
    try:
        logging.info(f"GitHubリポジトリにアクセス中: {repo_name}, ファイル: {file_path}")
        repo = github_client.get_repo(repo_name)
        content_file = repo.get_contents(file_path, ref=branch)
        # Handle both single file and list of files
        if isinstance(content_file, list):
            content_file = content_file[0]
        return content_file.decoded_content.decode("utf-8")
    except GithubException as e:
        logging.error(f"GitHubからのファイル取得エラー (repo: {repo_name}, file: {file_path}): {e}")
        return None

def create_github_pr(repo_name: str, new_branch_name: str, file_path: str, new_content: str, commit_message: str, pr_title: str) -> Optional[str]:
    """GitHubに新しいブランチを作成し、ファイルを更新してPRを作成する"""
    try:
        repo = github_client.get_repo(repo_name)
        source_branch = repo.get_branch("main")
        
        # 新しいブランチを作成
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=source_branch.commit.sha)

        # ファイルを更新 (または新規作成)
        try:
            contents = repo.get_contents(file_path, ref=new_branch_name)
            # Handle both single file and list of files
            if isinstance(contents, list):
                contents = contents[0]
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

def create_confluence_page(space_key: str, title: str, content: str, parent_id: Optional[str] = None) -> Optional[str]:
    """Confluenceページを作成する"""
    if not CONFLUENCE_ENABLED or not confluence_client:
        logging.error("Confluenceが有効になっていません")
        return None
    
    try:
        logging.info(f"Confluenceページを作成中: {title} (スペース: {space_key})")
        
        # マークダウンをConfluence形式のHTMLに変換
        html_content = markdown.markdown(content, extensions=['tables', 'fenced_code', 'toc'])
        
        # ページ作成
        page_data = {
            'type': 'page',
            'title': title,
            'space': {'key': space_key},
            'body': {
                'storage': {
                    'value': html_content,
                    'representation': 'storage'
                }
            }
        }
        
        if parent_id:
            page_data['ancestors'] = [{'id': parent_id}]
        
        result = confluence_client.create_page(
            space=space_key,
            title=title,
            body=html_content,
            parent_id=parent_id
        )
        
        page_id = result['id']
        page_url = f"{CONFLUENCE_URL}/pages/viewpage.action?pageId={page_id}"
        
        logging.info(f"Confluenceページが作成されました: {page_url}")
        return page_url
        
    except Exception as e:
        logging.error(f"Confluenceページ作成エラー: {e}")
        return None

def get_confluence_page_content(page_url: str) -> str | None:
    """ConfluenceページのURLから内容を取得する"""
    if not CONFLUENCE_ENABLED or not confluence_client:
        logging.error("Confluenceが有効になっていません")
        return None
    
    try:
        logging.info(f"Confluenceページから内容を取得中: {page_url}")
        
        # URLからページIDを抽出
        page_id_match = re.search(r'pageId=(\d+)', page_url)
        if not page_id_match:
            # 別のURL形式を試行
            page_id_match = re.search(r'/pages/(\d+)/', page_url)
        
        if not page_id_match:
            logging.error(f"ページIDをURLから抽出できませんでした: {page_url}")
            return None
        
        page_id = page_id_match.group(1)
        
        # ページ内容を取得
        page = confluence_client.get_page_by_id(page_id, expand='body.storage')
        
        if not page:
            logging.error(f"ページが見つかりませんでした: {page_id}")
            return None
        
        # HTML内容をテキストに変換
        html_content = page['body']['storage']['value']
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text(separator='\n', strip=True)
        
        logging.info(f"Confluenceページ内容を取得しました: {len(text_content)}文字")
        return text_content
        
    except Exception as e:
        logging.error(f"Confluenceページ取得エラー: {e}")
        return None

def generate_design_document(project_name: str, feature_name: str, requirements: str) -> str:
    """Claude APIを使用して設計ドキュメントを生成する"""
    prompt = f"""
あなたはシニアシステムアーキテクトです。以下の要件に基づいて詳細な設計ドキュメントを作成してください。

プロジェクト: {project_name}
機能: {feature_name}
要件: {requirements}

以下の形式で設計ドキュメントを作成してください：

# {feature_name} 設計書

## 概要
[機能の概要と目的]

## 要件
### 機能要件
[具体的な機能要件]

### 非機能要件
[パフォーマンス、セキュリティ、可用性等]

## アーキテクチャ
### システム構成
[システム全体の構成と各コンポーネントの役割]

### データフロー
[データの流れと処理の流れ]

## API設計
### エンドポイント一覧
[REST APIエンドポイントの詳細]

### リクエスト/レスポンス
[各APIのリクエスト・レスポンス形式]

## データベース設計
### テーブル設計
[必要なテーブルとカラム定義]

### リレーション
[テーブル間の関係性]

## セキュリティ考慮事項
[認証、認可、データ保護等のセキュリティ要件]

## 実装方針
### 技術選定
[使用する技術スタックと選定理由]

### コーディング規約
[命名規則、コードスタイル等]

## テスト戦略
[テスト方針とテストケースの概要]

## 運用考慮事項
[ログ、監視、デプロイメント等]

詳細で実装に役立つ設計書を作成してください。
"""
    
    try:
        logging.info("設計ドキュメントを生成中...")
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        design_content = response.content[0].text
        logging.info(f"設計ドキュメントが生成されました: {len(design_content)}文字")
        return design_content
        
    except AnthropicError as e:
        logging.error(f"設計ドキュメント生成エラー: {e}")
        return f"設計ドキュメントの生成中にエラーが発生しました: {e}"

def generate_code_from_design(design_content: str, file_path: str, additional_requirements: str = "") -> str:
    """設計ドキュメントからコードを生成する"""
    prompt = f"""
あなたはシニアソフトウェアエンジニアです。以下の設計ドキュメントに基づいてコードを実装してください。

設計ドキュメント:
{design_content}

実装対象ファイル: {file_path}
追加要件: {additional_requirements}

設計書の内容に忠実に、以下の点を考慮して実装してください：
- コードの可読性と保守性
- 適切なエラーハンドリング
- セキュリティベストプラクティス
- テスタビリティを考慮した設計
- パフォーマンスの最適化
- 適切なコメントとドキュメント

実装後のコード全体のみを、コードブロックなしで返してください。
"""
    
    try:
        logging.info("設計ベースコード生成中...")
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        code_content = response.content[0].text
        logging.info(f"設計ベースコードが生成されました: {len(code_content)}文字")
        return code_content
        
    except AnthropicError as e:
        logging.error(f"設計ベースコード生成エラー: {e}")
        return f"# コード生成エラー\n# {e}"

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

def process_design_task(body, response_url):
    """設計ドキュメント作成タスクの処理"""
    try:
        # Slackからの指示テキストをパース
        # 例: "my-app の ユーザー認証機能 について JWT認証を使用し、ログイン・ログアウト機能を含む"
        text = body.get("text", "")
        logging.info(f"受信した設計コマンド: {text}")
        
        def send_message(text):
            requests.post(response_url, json={"text": text})
        
        # コマンド形式の解析
        parts = text.split(" の ", 1)
        if len(parts) < 2:
            send_message("コマンドの形式が正しくありません。\n例: `/design プロジェクト名 の 機能名 について 要件内容`")
            return
            
        project_name = parts[0]
        parts = parts[1].split(" について ", 1)
        if len(parts) < 2:
            send_message("コマンドの形式が正しくありません。\n例: `/design プロジェクト名 の 機能名 について 要件内容`")
            return
            
        feature_name = parts[0]
        requirements = parts[1]
        
        logging.info(f"設計解析結果 - プロジェクト: {project_name}, 機能: {feature_name}, 要件: {requirements}")
        
        if not CONFLUENCE_ENABLED:
            send_message("⚠️ Confluence機能が有効になっていません。環境変数を確認してください。")
            return
        
        # 1. 設計ドキュメント生成
        send_message(f"📋 `{project_name}`の`{feature_name}`機能の設計ドキュメントを生成中...")
        design_content = generate_design_document(project_name, feature_name, requirements)
        
        # 2. Confluenceページ作成
        send_message("📝 Confluenceに設計ドキュメントを作成中...")
        page_title = f"{project_name} - {feature_name} 設計書"
        page_url = create_confluence_page(CONFLUENCE_SPACE_KEY, page_title, design_content)
        
        if page_url:
            send_message(f"✅ 設計ドキュメントの作成が完了しました！\n📄 設計書: {page_url}\n\n💡 開発を開始するには `/develop-from-design {page_url} の [ファイルパス] に実装` を使用してください。")
        else:
            send_message("❌ Confluenceページの作成中にエラーが発生しました。詳細はログを確認してください。")
            
    except Exception as e:
        logging.error(f"設計タスク処理エラー: {e}")
        requests.post(response_url, json={"text": f"設計ドキュメント作成中にエラーが発生しました: {e}"})

def process_design_based_development_task(body, response_url):
    """設計ベース開発タスクの処理"""
    try:
        # Slackからの指示テキストをパース
        # 例: "https://company.atlassian.net/wiki/spaces/DEV/pages/123456/User-Auth の auth.py に実装"
        text = body.get("text", "")
        logging.info(f"受信した設計ベース開発コマンド: {text}")
        
        def send_message(text):
            requests.post(response_url, json={"text": text})
        
        # コマンド形式の解析
        parts = text.split(" の ", 1)
        if len(parts) < 2:
            send_message("コマンドの形式が正しくありません。\n例: `/develop-from-design [confluence-url] の [ファイルパス] に実装`")
            return
            
        confluence_url = parts[0]
        parts = parts[1].split(" に実装", 1)
        if len(parts) < 1:
            send_message("コマンドの形式が正しくありません。\n例: `/develop-from-design [confluence-url] の [ファイルパス] に実装`")
            return
            
        file_path = parts[0]
        additional_requirements = parts[1] if len(parts) > 1 else ""
        
        logging.info(f"設計ベース開発解析結果 - URL: {confluence_url}, ファイル: {file_path}")
        
        if not CONFLUENCE_ENABLED:
            send_message("⚠️ Confluence機能が有効になっていません。環境変数を確認してください。")
            return
        
        # 1. Confluenceから設計ドキュメント取得
        send_message(f"📖 Confluenceから設計ドキュメントを取得中...")
        design_content = get_confluence_page_content(confluence_url)
        
        if not design_content:
            send_message("❌ Confluenceページから設計ドキュメントを取得できませんでした。URLを確認してください。")
            return
        
        # 2. 設計ベースコード生成
        send_message(f"🤖 設計ドキュメントに基づいて`{file_path}`のコードを生成中...")
        generated_code = generate_code_from_design(design_content, file_path, additional_requirements)
        
        # 3. GitHubからリポジトリ情報を推測またはユーザーに確認
        # 今回は簡単のため、事前設定されたリポジトリを使用
        # 実際の実装では、設計ドキュメントからリポジトリ情報を取得するか、
        # ユーザーに入力を求める機能を追加する必要があります
        send_message("⚠️ 注意: 現在のバージョンでは、GitHubリポジトリの自動特定はサポートされていません。\n手動で以下のコードをリポジトリに追加してください。")
        
        # コードをSlackに送信（長い場合は一部のみ）
        code_preview = generated_code[:1000] + "..." if len(generated_code) > 1000 else generated_code
        send_message(f"```\n{code_preview}\n```")
        
        # 将来の改善提案
        send_message("💡 改善提案: `/develop-with-design [confluence-url] [owner/repo] の [ファイルパス] に実装` のような形式で、リポジトリを指定できるようにすることを検討中です。")
        
    except Exception as e:
        logging.error(f"設計ベース開発タスク処理エラー: {e}")
        requests.post(response_url, json={"text": f"設計ベース開発中にエラーが発生しました: {e}"})

@app.command("/design")
def handle_design_command(ack, body, say):
    """設計ドキュメント作成コマンドのハンドラー"""
    # Slackの3秒タイムアウトに応答
    ack(f"設計依頼を受け付けました: `{body['text']}`\n設計ドキュメントの生成を開始します...")
    
    # バックグラウンドでタスクを実行
    thread = threading.Thread(target=process_design_task, args=(body, body['response_url']))
    thread.start()

@app.command("/develop-from-design")
def handle_develop_from_design_command(ack, body, say):
    """設計ベース開発コマンドのハンドラー"""
    # Slackの3秒タイムアウトに応答
    ack(f"設計ベース開発依頼を受け付けました: `{body['text']}`\n設計ドキュメントの解析を開始します...")
    
    # バックグラウンドでタスクを実行
    thread = threading.Thread(target=process_design_based_development_task, args=(body, body['response_url']))
    thread.start()

async def process_design_task_mcp(body, response_url):
    """MCP版設計ドキュメント作成タスクの処理"""
    try:
        # Slackからの指示テキストをパース
        text = body.get("text", "")
        logging.info(f"受信したMCP設計コマンド: {text}")
        
        def send_message(text):
            requests.post(response_url, json={"text": text})
        
        if not MCP_AVAILABLE:
            send_message("⚠️ Atlassian MCP機能が利用できません。従来の方式で処理します...")
            # フォールバックとして従来の処理を実行
            return process_design_task(body, response_url)
        
        # コマンド形式の解析
        parts = text.split(" の ", 1)
        if len(parts) < 2:
            send_message("コマンドの形式が正しくありません。\n例: `/design-mcp プロジェクト名 の 機能名 について 要件内容`")
            return
            
        project_name = parts[0]
        parts = parts[1].split(" について ", 1)
        if len(parts) < 2:
            send_message("コマンドの形式が正しくありません。\n例: `/design-mcp プロジェクト名 の 機能名 について 要件内容`")
            return
            
        feature_name = parts[0]
        requirements = parts[1]
        
        logging.info(f"MCP設計解析結果 - プロジェクト: {project_name}, 機能: {feature_name}, 要件: {requirements}")
        
        # 1. MCP版設計ドキュメント生成
        send_message(f"🤖 `{project_name}`の`{feature_name}`機能の設計ドキュメントをMCP経由で生成中...")
        design_content = await generate_design_document_mcp(project_name, feature_name, requirements)
        
        # 2. MCP経由でConfluenceページ作成
        send_message("📝 Atlassian MCP経由でConfluenceに設計ドキュメントを作成中...")
        page_title = f"{project_name} - {feature_name} 設計書"
        
        # デフォルトスペースキーを使用（環境変数から取得、なければDEV）
        default_space = os.environ.get("CONFLUENCE_SPACE_KEY", "DEV").strip()
        
        result = await create_confluence_page_mcp(default_space, page_title, design_content)
        
        if result["success"]:
            page_url = result.get("page_url", "URLの抽出に失敗")
            send_message(f"✅ MCP経由での設計ドキュメント作成が完了しました！\n📄 設計書: {page_url}\n\n💡 開発を開始するには `/develop-from-design-mcp {page_url} の [ファイルパス] に実装` を使用してください。")
            
            # 詳細な作成結果も送信
            if result.get("response"):
                # レスポンスが長い場合は一部のみ表示
                response_preview = result["response"][:500] + "..." if len(result["response"]) > 500 else result["response"]
                send_message(f"📋 作成詳細:\n```{response_preview}```")
        else:
            error_msg = result.get("error", "不明なエラー")
            send_message(f"❌ MCP経由でのConfluenceページ作成中にエラーが発生しました:\n{error_msg}")
            
    except Exception as e:
        logging.error(f"MCP設計タスク処理エラー: {e}")
        requests.post(response_url, json={"text": f"MCP設計ドキュメント作成中にエラーが発生しました: {e}"})

async def process_design_based_development_task_mcp(body, response_url):
    """MCP版設計ベース開発タスクの処理"""
    try:
        # Slackからの指示テキストをパース
        text = body.get("text", "")
        logging.info(f"受信したMCP設計ベース開発コマンド: {text}")
        
        def send_message(text):
            requests.post(response_url, json={"text": text})
        
        if not MCP_AVAILABLE:
            send_message("⚠️ Atlassian MCP機能が利用できません。従来の方式で処理します...")
            # フォールバックとして従来の処理を実行
            return process_design_based_development_task(body, response_url)
        
        # コマンド形式の解析
        parts = text.split(" の ", 1)
        if len(parts) < 2:
            send_message("コマンドの形式が正しくありません。\n例: `/develop-from-design-mcp [confluence-url] の [ファイルパス] に実装`")
            return
            
        confluence_url = parts[0]
        parts = parts[1].split(" に実装", 1)
        if len(parts) < 1:
            send_message("コマンドの形式が正しくありません。\n例: `/develop-from-design-mcp [confluence-url] の [ファイルパス] に実装`")
            return
            
        file_path = parts[0]
        additional_requirements = parts[1] if len(parts) > 1 else ""
        
        logging.info(f"MCP設計ベース開発解析結果 - URL: {confluence_url}, ファイル: {file_path}")
        
        # 1. MCP経由でConfluenceから設計ドキュメント取得
        send_message(f"📖 Atlassian MCP経由でConfluenceから設計ドキュメントを取得中...")
        page_result = await get_confluence_page_mcp(confluence_url)
        
        if not page_result["success"]:
            error_msg = page_result.get("error", "不明なエラー")
            send_message(f"❌ MCP経由でのConfluenceページ取得に失敗しました:\n{error_msg}")
            return
        
        design_content = page_result["content"]
        
        # 2. 設計ベースコード生成
        send_message(f"🤖 MCP取得の設計ドキュメントに基づいて`{file_path}`のコードを生成中...")
        generated_code = generate_code_from_design(design_content, file_path, additional_requirements)
        
        # 3. 生成されたコードを提供
        send_message("✅ MCP経由での設計ベースコード生成が完了しました！")
        
        # コードをSlackに送信（長い場合は一部のみ）
        code_preview = generated_code[:1000] + "..." if len(generated_code) > 1000 else generated_code
        send_message(f"```{file_path}\n{code_preview}\n```")
        
        # 取得した設計ドキュメント情報も送信
        design_preview = design_content[:300] + "..." if len(design_content) > 300 else design_content
        send_message(f"📋 参考にした設計書の内容:\n```{design_preview}```")
        
        # 将来の改善提案
        send_message("💡 改善提案: 今後、MCP経由でGitHubへの自動PR作成機能も追加予定です。")
        
    except Exception as e:
        logging.error(f"MCP設計ベース開発タスク処理エラー: {e}")
        requests.post(response_url, json={"text": f"MCP設計ベース開発中にエラーが発生しました: {e}"})

@app.command("/design-mcp")
def handle_design_command_mcp(ack, body, say):
    """MCP版設計ドキュメント作成コマンドのハンドラー"""
    # Slackの3秒タイムアウトに応答
    ack(f"🤖 MCP設計依頼を受け付けました: `{body['text']}`\nAtlassian MCP経由で設計ドキュメントの生成を開始します...")
    
    # バックグラウンドでタスクを実行
    run_async_safely(process_design_task_mcp(body, body['response_url']))

@app.command("/develop-from-design-mcp")
def handle_develop_from_design_command_mcp(ack, body, say):
    """MCP版設計ベース開発コマンドのハンドラー"""
    # Slackの3秒タイムアウトに応答
    ack(f"🤖 MCP設計ベース開発依頼を受け付けました: `{body['text']}`\nAtlassian MCP経由で設計ドキュメントの解析を開始します...")
    
    # バックグラウンドでタスクを実行
    run_async_safely(process_design_based_development_task_mcp(body, body['response_url']))

@app.command("/confluence-search")
def handle_confluence_search_command(ack, body, say):
    """Confluence検索コマンドのハンドラー"""
    # Slackの3秒タイムアウトに応答
    ack(f"🔍 Confluence検索依頼を受け付けました: `{body['text']}`\nAtlassian MCP経由で検索を開始します...")
    
    async def process_search():
        try:
            text = body.get("text", "")
            
            def send_message(text):
                requests.post(body['response_url'], json={"text": text})
            
            if not MCP_AVAILABLE:
                send_message("⚠️ Atlassian MCP機能が利用できません。")
                return
            
            if not text.strip():
                send_message("検索クエリを指定してください。\n例: `/confluence-search ユーザー認証`")
                return
            
            # スペース指定の解析（オプション）
            parts = text.split(" in:", 1)
            query = parts[0].strip()
            space_key = parts[1].strip() if len(parts) > 1 else None
            
            # MCP経由で検索実行
            send_message(f"🔍 「{query}」を検索中...")
            result = await search_confluence_pages_mcp(query, space_key)
            
            if result["success"]:
                send_message(f"✅ 検索完了しました！\n\n{result['results']}")
            else:
                error_msg = result.get("error", "不明なエラー")
                send_message(f"❌ 検索中にエラーが発生しました:\n{error_msg}")
                
        except Exception as e:
            logging.error(f"Confluence検索エラー: {e}")
            requests.post(body['response_url'], json={"text": f"検索中にエラーが発生しました: {e}"})
    
    # バックグラウンドでタスクを実行
    run_async_safely(process_search())

# Socket Mode の初期化は main.py で行います（Cloud Run用）

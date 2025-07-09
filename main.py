#!/usr/bin/env python3
"""
Google Cloud Functions用のエントリーポイント
Slack AI開発ボットをCloud Functionsで実行
"""

import os
import logging
import asyncio
import threading
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import functions_framework

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# aibot.pyから必要なコンポーネントをインポート
from aibot import (
    app as slack_app,
    process_development_task,
    process_design_task,
    process_design_based_development_task,
    process_design_task_mcp,
    process_design_based_development_task_mcp
)

# SlackRequestHandlerを初期化
handler = SlackRequestHandler(slack_app)

@functions_framework.http
def slack_bot(request):
    """
    Cloud Functions用のHTTPエントリーポイント
    
    Args:
        request: Google Cloud Functions HTTPリクエスト
        
    Returns:
        Response: HTTPレスポンス
    """
    try:
        # リクエストのログ出力
        logging.info(f"受信リクエスト: {request.method} {request.path}")
        
        # Slack Boltハンドラーにリクエストを渡す
        return handler.handle(request)
        
    except Exception as e:
        logging.error(f"Cloud Functions処理エラー: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Flask アプリケーションも作成（ローカルテスト用）
flask_app = Flask(__name__)

@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """ローカルテスト用のエンドポイント"""
    return handler.handle(request)

@flask_app.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({"status": "healthy", "service": "slack-ai-bot"}), 200

# ローカル実行時の処理
if __name__ == "__main__":
    logging.info("🤖 Slack AI開発ボット（Cloud Functions版）をローカルで起動します...")
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Starting Flask app on port {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False)
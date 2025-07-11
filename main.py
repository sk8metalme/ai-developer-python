#!/usr/bin/env python3
"""
Google Cloud Run エントリーポイント
Slack Bot機能統合版
"""

import os
import logging
import threading
import time
from flask import Flask, jsonify
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Flaskアプリ作成（Gunicorn用）
flask_app = Flask(__name__)

# Gunicorn用のappオブジェクト（Flask用）
application = flask_app

@flask_app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "running",
        "service": "slack-ai-bot",
        "version": "3.0"
    }), 200

@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "slack-ai-bot"
    }), 200

@flask_app.route("/debug", methods=["GET"])
def debug():
    """デバッグ情報エンドポイント"""
    env_info = {
        "PORT": os.environ.get("PORT"),
        "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT"),
        "ENVIRONMENT": os.environ.get("ENVIRONMENT"),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL"),
        "PYTHONUNBUFFERED": os.environ.get("PYTHONUNBUFFERED")
    }
    
    return jsonify({
        "message": "Debug information",
        "environment": env_info,
        "slack_ready": slack_handler_ready if 'slack_handler_ready' in globals() else False
    }), 200

# Slack Bot機能の統合
slack_handler_ready = False

def start_slack_bot():
    """Slack Botをバックグラウンドで起動"""
    global slack_handler_ready
    try:
        logger.info("🤖 Slack Bot初期化中...")
        
        # aibot.pyからSlack Appをインポート
        from aibot import app as slack_app, SLACK_APP_TOKEN
        
        # Socket Modeハンドラーの開始
        if not os.environ.get("GITHUB_ACTIONS"):  # ビルド時はスキップ
            handler = SocketModeHandler(slack_app, SLACK_APP_TOKEN)
            logger.info("🚀 Slack Bot（Socket Mode）を開始します...")
            slack_handler_ready = True
            handler.start()  # ブロッキング呼び出し
        else:
            logger.info("⚠️ GitHub Actions環境のためSlack Bot起動をスキップします")
            slack_handler_ready = False
            
    except Exception as e:
        logger.error(f"❌ Slack Bot起動エラー: {e}")
        import traceback
        logger.error(f"トレースバック: {traceback.format_exc()}")
        slack_handler_ready = False

# メイン実行時の処理
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 統合版 Slack AI Bot 起動中 - Port: {port}")
    
    # Slack Botをバックグラウンドで起動
    if not os.environ.get("GITHUB_ACTIONS"):
        slack_thread = threading.Thread(target=start_slack_bot, daemon=True)
        slack_thread.start()
        time.sleep(2)  # Slack Bot初期化の時間を確保
    
    try:
        flask_app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            threaded=True
        )
        logger.info("✅ サーバー起動成功")
    except Exception as e:
        logger.error(f"❌ サーバー起動失敗: {e}")
        import traceback
        logger.error(f"トレースバック: {traceback.format_exc()}")
        exit(1)
else:
    # Gunicorn実行時（本番環境）
    logger.info("🔧 Gunicorn環境でSlack Bot統合版を起動中...")
    
    # Slack Botをバックグラウンドで起動
    if not os.environ.get("GITHUB_ACTIONS"):
        slack_thread = threading.Thread(target=start_slack_bot, daemon=True)
        slack_thread.start()
        logger.info("🤖 Slack Bot（Socket Mode）をバックグラウンドで開始しました")

# Gunicorn用のapp参照
app = flask_app
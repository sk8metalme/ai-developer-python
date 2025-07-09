#!/usr/bin/env python3
"""
Google Cloud Run エントリーポイント (Socket Mode + Health Check Server)
aibot.py をGoogle Cloud Run で実行するためのラッパー
"""

import os
import logging
import signal
import sys
import threading
from flask import Flask, jsonify

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# ヘルスチェック用のFlaskアプリ
health_app = Flask(__name__)

@health_app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "slack-ai-bot-socket-mode"}), 200

@health_app.route("/", methods=["GET"])
def root():
    return jsonify({"status": "Socket Mode Active", "service": "slack-ai-bot"}), 200

def run_health_server():
    """ヘルスチェック用サーバーを起動"""
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting health check server on port {port}")
    health_app.run(host="0.0.0.0", port=port, debug=False)

def signal_handler(sig, frame):
    """シグナルハンドラー"""
    logger.info('Socket Mode を終了します...')
    sys.exit(0)

if __name__ == "__main__":
    logger.info("🤖 Slack AI開発ボット (Socket Mode + Health Check) を起動します...")
    
    # シグナルハンドラーの設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # ヘルスチェックサーバーをバックグラウンドで起動
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Socket Mode Handler の初期化と起動
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    from aibot import app, SLACK_APP_TOKEN
    
    socket_mode_handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    logger.info("Socket Mode で接続を開始します...")
    socket_mode_handler.start()
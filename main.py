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
    health_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

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
    
    # Socket Mode の初期化を遅延実行
    def delayed_socket_mode_init():
        import time
        time.sleep(3)  # ヘルスチェックサーバーの起動を待つ
        try:
            logger.info("Socket Mode の初期化を開始します...")
            from slack_bolt.adapter.socket_mode import SocketModeHandler
            from aibot import app, SLACK_APP_TOKEN
            
            logger.info(f"Socket Mode App Token: {SLACK_APP_TOKEN[:10]}..." if SLACK_APP_TOKEN else "SLACK_APP_TOKEN not found")
            socket_mode_handler = SocketModeHandler(app, SLACK_APP_TOKEN)
            logger.info("Socket Mode で接続を開始します...")
            
            # Socket Mode を開始（ブロッキング）
            socket_mode_handler.start()
            
        except Exception as e:
            logger.error(f"Socket Mode 初期化エラー: {e}")
            logger.info("ヘルスチェックサーバーのみ継続して動作します...")
    
    # Socket Mode を別スレッドで遅延実行
    socket_thread = threading.Thread(target=delayed_socket_mode_init, daemon=False)
    socket_thread.start()
    
    # メインスレッドは無限ループで待機（ヘルスチェックサーバーが動作し続ける）
    import time
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("アプリケーションを終了します...")
        sys.exit(0)
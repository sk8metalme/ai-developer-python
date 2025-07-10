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
    logging.info(f"Starting health check server on port {port}")
    health_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

def signal_handler(sig, frame):
    """シグナルハンドラー"""
    logging.info('Socket Mode を終了します...')
    sys.exit(0)

if __name__ == "__main__":
    logging.info("🤖 Slack AI開発ボット (Socket Mode + Health Check) を起動します...")
    
    # シグナルハンドラーの設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Socket Mode の初期化を別スレッドで実行（失敗してもヘルスサーバーは継続）
    def delayed_socket_mode_init():
        import time
        time.sleep(5)  # ヘルスチェックサーバーの起動を待つ
        try:
            logging.info("Socket Mode の初期化を開始します...")
            
            # aibot.py のimportを慎重に実行
            try:
                from aibot import app, SLACK_APP_TOKEN
                logging.info("✅ aibot.py を正常にimportしました")
            except Exception as import_error:
                logging.error(f"❌ aibot.py のimportでエラー: {import_error}")
                logging.info("ヘルスチェックサーバーのみで動作を継続します")
                return
            
            # Socket Mode Handlerの初期化
            from slack_bolt.adapter.socket_mode import SocketModeHandler
            
            if not SLACK_APP_TOKEN:
                logging.warning("SLACK_APP_TOKEN が設定されていません。Socket Mode をスキップします。")
                return
                
            logging.info(f"Socket Mode App Token: {SLACK_APP_TOKEN[:10]}...")
            socket_mode_handler = SocketModeHandler(app, SLACK_APP_TOKEN)
            logging.info("Socket Mode で接続を開始します...")
            
            # Socket Mode を開始（ブロッキング）
            socket_mode_handler.start()
            
        except Exception as e:
            logging.error(f"Socket Mode 初期化エラー: {e}")
            logging.info("ヘルスチェックサーバーのみ継続して動作します...")
    
    # Socket Mode を別スレッドで遅延実行（daemon=True で失敗しても影響しない）
    socket_thread = threading.Thread(target=delayed_socket_mode_init, daemon=True)
    socket_thread.start()
    
    # メインスレッドでヘルスチェックサーバーを実行（Cloud Runに必須）
    logging.info("メインスレッドでヘルスチェックサーバーを開始します...")
    try:
        run_health_server()  # メインスレッドで実行（ブロッキング）
    except Exception as e:
        logging.error(f"ヘルスチェックサーバー エラー: {e}")
        sys.exit(1)
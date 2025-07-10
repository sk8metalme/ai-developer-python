#!/usr/bin/env python3
"""
Google Cloud Run エントリーポイント (Socket Mode + Health Check Server)
確実にport 8080でリッスンする簡潔な実装
"""

import os
import logging
import sys
import threading
import time
from flask import Flask, jsonify

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_health_app():
    """ヘルスチェック用のFlaskアプリを作成"""
    app = Flask(__name__)
    
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy", "service": "slack-ai-bot"}), 200

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({"status": "running", "service": "slack-ai-bot"}), 200
    
    return app

def initialize_socket_mode():
    """Socket Modeを安全に初期化（別スレッド）"""
    def socket_mode_worker():
        time.sleep(10)  # ヘルスサーバーの完全起動を待つ
        
        try:
            logger.info("🔌 Socket Mode初期化を開始...")
            
            # 環境変数の基本チェック
            if os.environ.get("GITHUB_ACTIONS"):
                logger.info("GitHub Actions環境でのビルド - Socket Modeスキップ")
                return
            
            # aibot.pyのimportを試行
            try:
                logger.info("📦 aibot.pyをimport中...")
                from aibot import app as slack_app, SLACK_APP_TOKEN
                logger.info("✅ aibot.py import成功")
                
                if not SLACK_APP_TOKEN:
                    logger.warning("⚠️ SLACK_APP_TOKEN未設定 - Socket Modeスキップ")
                    return
                
                logger.info(f"🔑 SLACK_APP_TOKEN: {SLACK_APP_TOKEN[:10]}...")
                
                # Socket Mode Handler起動
                from slack_bolt.adapter.socket_mode import SocketModeHandler
                handler = SocketModeHandler(slack_app, SLACK_APP_TOKEN)
                
                logger.info("🚀 Socket Mode接続開始...")
                handler.start()  # ブロッキング実行
                
            except ImportError as e:
                logger.error(f"❌ aibot.py import失敗: {e}")
                logger.info("ヘルスチェックサーバーのみで継続")
            except Exception as e:
                logger.error(f"❌ Socket Mode初期化エラー: {e}")
                logger.info("ヘルスチェックサーバーのみで継続")
                
        except Exception as e:
            logger.error(f"❌ Socket Mode worker予期せぬエラー: {e}")
    
    # Socket Modeを別スレッドで実行（失敗してもヘルスサーバーに影響しない）
    socket_thread = threading.Thread(target=socket_mode_worker, daemon=True)
    socket_thread.start()
    logger.info("🔌 Socket Mode初期化スレッド開始")

def main():
    """メイン関数 - 確実にヘルスサーバーを起動"""
    logger.info("🤖 Slack AI Bot (Cloud Run) 起動開始...")
    
    # ポート設定
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🌐 ポート設定: {port}")
    
    # Flaskアプリ作成
    health_app = create_health_app()
    logger.info("✅ ヘルスチェックアプリ作成完了")
    
    # Socket Mode初期化（非ブロッキング）
    initialize_socket_mode()
    
    # メインスレッドでヘルスサーバー実行（最優先）
    try:
        logger.info(f"🚀 ヘルスチェックサーバー起動中 (port:{port})...")
        health_app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ ヘルスサーバー起動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
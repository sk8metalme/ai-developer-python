#!/usr/bin/env python3
"""
Google Cloud Run エントリーポイント
段階的にSlack機能を追加する戦略
"""

import os
import logging
from flask import Flask, jsonify

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Flaskアプリ作成
app = Flask(__name__)

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "running",
        "service": "slack-ai-bot",
        "version": "2.0"
    }), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "slack-ai-bot"
    }), 200

@app.route("/debug", methods=["GET"])
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
        "slack_ready": False  # 今回はシンプル版
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 シンプル版 Slack AI Bot 起動中 - Port: {port}")
    
    try:
        app.run(
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
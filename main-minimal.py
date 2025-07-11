#!/usr/bin/env python3
"""
最小限のCloud Run用ヘルスサーバー
確実にport 8080でリッスンするテスト用実装
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
        "service": "slack-ai-bot-minimal",
        "port": os.environ.get("PORT", "8080")
    }), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "slack-ai-bot-minimal"
    }), 200

@app.route("/test", methods=["GET"])
def test():
    return jsonify({
        "message": "Cloud Run deployment test successful",
        "env_vars": {
            "PORT": os.environ.get("PORT"),
            "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT"),
            "LOG_LEVEL": os.environ.get("LOG_LEVEL")
        }
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 最小限ヘルスサーバー起動中 - Port: {port}")
    
    try:
        app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ サーバー起動失敗: {e}")
        exit(1)
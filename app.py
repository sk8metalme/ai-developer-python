#!/usr/bin/env python3
"""
Cloud Run用の最も基本的なFlaskアプリ
Gunicorn WSGIサーバーで実行
"""

import os
import logging
from flask import Flask, jsonify

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flaskアプリ作成
app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "message": "Hello from Cloud Run!",
        "service": "slack-ai-bot",
        "status": "running"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "slack-ai-bot"
    })

@app.route("/debug")
def debug():
    return jsonify({
        "port": os.environ.get("PORT", "8080"),
        "project": os.environ.get("GOOGLE_CLOUD_PROJECT", "not-set"),
        "environment": os.environ.get("ENVIRONMENT", "not-set")
    })

if __name__ == "__main__":
    # 開発用サーバー（本番ではGunicornを使用）
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
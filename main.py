#!/usr/bin/env python3
"""
Google Cloud Run エントリーポイント
aibot.py をGoogle Cloud Run で実行するためのラッパー
"""

import os
import logging
from aibot import flask_app

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Cloud Run でのポート設定
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"Starting Flask app on port {port}")
    
    # Flask アプリケーションを起動
    flask_app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
#!/usr/bin/env python3
"""
Google Cloud Run エントリーポイント (Socket Mode)
aibot.py をGoogle Cloud Run で実行するためのラッパー
"""

import os
import logging
import signal
import sys

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """シグナルハンドラー"""
    logger.info('Socket Mode を終了します...')
    sys.exit(0)

if __name__ == "__main__":
    logger.info("🤖 Slack AI開発ボット (Socket Mode) を起動します...")
    
    # シグナルハンドラーの設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Socket Mode Handler の初期化と起動
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    from aibot import app, SLACK_APP_TOKEN
    
    socket_mode_handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    logger.info("Socket Mode で接続を開始します...")
    socket_mode_handler.start()
# Makefile for AI Developer Bot

.PHONY: test test-unit test-integration test-coverage install clean help

# デフォルトターゲット
help:
	@echo "利用可能なコマンド:"
	@echo "  install       - 依存関係をインストール"
	@echo "  test          - 全てのテストを実行"
	@echo "  test-unit     - 単体テストのみ実行"
	@echo "  test-integration - 統合テストのみ実行"
	@echo "  test-coverage - カバレッジレポート付きでテスト実行"
	@echo "  clean         - テンポラリファイルを削除"
	@echo "  run           - ボットを実行"

# 依存関係のインストール
install:
	pip install -r requirements.txt

# 全てのテストを実行
test:
	python -m pytest test_aibot_pytest.py -v
	python -m unittest test_aibot.py -v

# 単体テストのみ実行
test-unit:
	python -m pytest test_aibot_pytest.py -v -m "not integration and not slow"

# 統合テストのみ実行
test-integration:
	python -m pytest test_aibot_pytest.py -v -m integration

# カバレッジレポート付きでテスト実行
test-coverage:
	pip install coverage
	coverage run -m pytest test_aibot_pytest.py
	coverage report -m
	coverage html

# テンポラリファイルの削除
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -f .coverage
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# ボットの実行
run:
	python aibot.py

# 開発環境のセットアップ
setup-dev: install
	@echo "開発環境の準備が完了しました"
	@echo "環境変数を設定してください: source setup-env.sh"
	@echo "テストを実行してください: make test"
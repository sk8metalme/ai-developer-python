# Project ID 管理ガイド

このプロジェクトでは、Google Cloud Project ID をGitリポジトリに含めることなく管理する方法を提供しています。

## 🔧 セットアップ方法

### 1. ローカル開発環境

```bash
# プロジェクト設定スクリプトを実行
./setup-project.sh

# または手動で設定
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud config set project your-project-id
```

### 2. 本番環境（Cloud Run）

Project IDは以下の優先順位で自動取得されます：

1. **環境変数 `GOOGLE_CLOUD_PROJECT`**（推奨）
2. **gcloud config のデフォルトプロジェクト**
3. **Cloud Run のメタデータサービス**（自動）

### 3. CI/CD（GitHub Actions）

GitHub Secretsで以下を設定：

- `GCP_SA_KEY`: サービスアカウントのJSON鍵
- プロジェクトIDは gcloud config から自動取得

## 📁 ファイル構成

```
├── .env.example          # 環境変数のテンプレート
├── .env.local           # ローカル設定（Git管理対象外）
├── setup-project.sh     # プロジェクト設定スクリプト
├── deploy.sh            # デプロイスクリプト（動的Project ID取得）
└── .github/workflows/
    └── deploy.yml       # CI/CD設定
```

## 🔒 セキュリティ

- **Project ID**: リポジトリに含めない
- **トークン・鍵**: Secret Manager で管理
- **設定ファイル**: .gitignore で除外

## 💡 メリット

1. **セキュリティ**: Project ID をパブリックリポジトリに露出しない
2. **柔軟性**: 異なる環境で異なるプロジェクトを使用可能
3. **自動化**: CI/CD で手動設定不要
4. **保守性**: 環境固有の設定を分離

## 🚀 デプロイ

```bash
# 1. プロジェクト設定
./setup-project.sh

# 2. Secret Manager 設定
gcloud secrets create SLACK_BOT_TOKEN
echo "xoxb-..." | gcloud secrets versions add SLACK_BOT_TOKEN --data-file=-

# 3. デプロイ実行
./deploy.sh
```

Project IDは自動的に検出・使用されます。
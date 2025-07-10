# GitHub Actions セットアップガイド

このガイドでは、GitHub ActionsでGoogle Cloud Runへの自動デプロイを設定する方法を説明します。

## 🚀 クイックスタート

### 1. サービスアカウントの作成

```bash
# プロジェクトの設定
gcloud config set project YOUR_PROJECT_ID

# GitHub Actions用サービスアカウントの作成
./setup-github-actions.sh
```

### 2. GitHubでのSecret設定

1. GitHub リポジトリの **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック
3. 以下のSecretを追加：

| Secret名 | 値 | 説明 |
|----------|-----|------|
| `GCP_SA_KEY` | `setup-github-actions.sh`の出力 | サービスアカウントのJSON鍵 |

### 3. デプロイの実行

- **自動デプロイ**: `main` ブランチにpushすると本番環境へデプロイ
- **手動デプロイ**: Actions タブから「Deploy to Cloud Run」を手動実行
- **PR デプロイ**: PR作成時にstagingへデプロイ

## 🎯 ワークフローの詳細

### デプロイワークフロー (`.github/workflows/deploy.yml`)

#### トリガー条件

- **main ブランチ**: 本番環境へデプロイ
- **PR**: staging環境へデプロイ  
- **手動実行**: 任意の環境を選択可能

#### 処理フロー

1. **認証**: サービスアカウントでGoogle Cloudに認証
2. **Project ID取得**: gcloud configから自動取得
3. **Docker Build**: Cloud Build でイメージをビルド
4. **デプロイ**: Cloud Run にデプロイ
5. **ヘルスチェック**: サービスの正常性確認
6. **レポート**: デプロイ結果をGitHubに表示

#### 環境別設定

| 環境 | サービス名 | インスタンス数 | ログレベル |
|------|-----------|---------------|-----------|
| **production** | `slack-ai-bot` | 1-10 | INFO |
| **staging** | `slack-ai-bot-staging` | 0-3 | DEBUG |
| **development** | `slack-ai-bot-development` | 0-1 | DEBUG |

### テストワークフロー (`.github/workflows/test.yml`)

#### 実行内容

- **構文チェック**: Python/Shell スクリプトの構文確認
- **依存関係**: requirements.txt の検証
- **Docker Build**: Dockerfileの検証
- **セキュリティ**: シークレット漏洩チェック
- **コード品質**: Lint、型チェック（オプション）

## 🔐 セキュリティ

### 権限管理

サービスアカウントには最小限の権限のみを付与：

```bash
roles/run.admin                    # Cloud Run管理
roles/cloudbuild.builds.builder    # Cloud Build実行
roles/storage.admin               # Container Registry
roles/secretmanager.secretAccessor # Secret Manager読み取り
roles/iam.serviceAccountUser      # サービスアカウント使用
roles/artifactregistry.admin     # Artifact Registry
```

### Secret管理

- **GitHub Secrets**: サービスアカウント鍵のみ
- **Google Secret Manager**: アプリケーションの機密情報
- **環境変数**: 非機密設定情報

## 🛠️ トラブルシューティング

### よくある問題

#### 1. Permission Denied エラー

```bash
# 権限確認
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" --format="table(bindings.role,bindings.members)"

# 権限再設定
./setup-github-actions.sh
```

#### 2. Project ID が取得できない

```bash
# gcloud設定確認
gcloud config list

# プロジェクト設定
gcloud config set project YOUR_PROJECT_ID
```

#### 3. Docker Build エラー

```bash
# ローカルでビルドテスト
docker build -t test-image .

# Cloud Build 権限確認
gcloud services enable cloudbuild.googleapis.com
```

#### 4. Secret Manager エラー

```bash
# Secret存在確認
gcloud secrets list

# Secret権限確認
gcloud secrets get-iam-policy SECRET_NAME
```

## 📊 監視とログ

### デプロイ状況の確認

1. **GitHub Actions**: リポジトリの Actions タブ
2. **Cloud Run**: Google Cloud Console の Cloud Run セクション
3. **ログ**: Cloud Logging で詳細ログ確認

### アラート設定

```bash
# Cloud Monitoring でアラート設定
gcloud alpha monitoring policies create --policy-from-file=monitoring-policy.yaml
```

## 🔄 継続的改善

### 推奨設定

1. **Branch Protection**: main ブランチの保護
2. **Required Reviews**: PR レビューの必須化
3. **Status Checks**: テストワークフローの成功を必須に
4. **Environment Protection**: 本番環境のデプロイ承認制

### 拡張機能

- **Slack通知**: デプロイ結果の通知
- **ロールバック**: 自動ロールバック機能
- **監視**: カスタムメトリクス監視
- **テスト**: 統合テストの追加

## 📝 関連ファイル

- `setup-github-actions.sh` - サービスアカウント作成
- `deploy.sh` - ローカルデプロイスクリプト
- `setup-project.sh` - プロジェクト初期設定
- `.github/workflows/deploy.yml` - デプロイワークフロー
- `.github/workflows/test.yml` - テストワークフロー
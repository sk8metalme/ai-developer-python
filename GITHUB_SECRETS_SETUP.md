# GitHub Secrets 設定ガイド

## 🔐 設定する2つのSecrets

### 1. WIF_PROVIDER
```
Name: WIF_PROVIDER
Value: projects/224087487695/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider
```

### 2. WIF_SERVICE_ACCOUNT
```
Name: WIF_SERVICE_ACCOUNT
Value: github-actions-deploy@ai-developer-465404.iam.gserviceaccount.com
```

## 📋 設定手順

### ステップ1: リポジトリ設定へアクセス
1. https://github.com/sk8metalme/ai-developer-python を開く
2. `Settings` タブをクリック
3. 左サイドバーの `Secrets and variables` をクリック
4. `Actions` を選択

### ステップ2: 最初のSecretを追加
1. `New repository secret` ボタンをクリック
2. Name: `WIF_PROVIDER`
3. Value: `projects/224087487695/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider`
4. `Add secret` をクリック

### ステップ3: 2つ目のSecretを追加
1. 再度 `New repository secret` ボタンをクリック
2. Name: `WIF_SERVICE_ACCOUNT`
3. Value: `github-actions-deploy@ai-developer-465404.iam.gserviceaccount.com`
4. `Add secret` をクリック

## ✅ 設定完了の確認

設定後、Actions secrets一覧に以下が表示されます：
- ✅ WIF_PROVIDER
- ✅ WIF_SERVICE_ACCOUNT

## 🚀 次のステップ

Secrets設定完了後は：
1. mainブランチにコードをpush
2. GitHub Actionsが自動的にCloud Runにデプロイ
3. Actions タブでデプロイ状況を確認

## 🔍 トラブルシューティング

### 設定が見つからない場合
- リポジトリのオーナー権限が必要です
- プライベートリポジトリの場合は、適切なアクセス権限を確認

### デプロイエラーの場合
- Actions タブでエラーログを確認
- Google Cloud の権限設定を再確認
- setup-github-actions-workload-identity.sh を再実行
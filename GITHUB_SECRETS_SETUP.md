# GitHub Secrets 設定ガイド

## 🔐 設定する2つのSecrets

### 1. WIF_PROVIDER
```
Name: WIF_PROVIDER
Value: setup-github-actions-workload-identity.sh の実行結果で出力される値
```

### 2. WIF_SERVICE_ACCOUNT
```
Name: WIF_SERVICE_ACCOUNT
Value: setup-github-actions-workload-identity.sh の実行結果で出力される値
```

## 📋 設定手順

### ステップ1: Setup スクリプトを実行
1. `setup-github-actions-workload-identity.sh` を実行
2. 実行結果の「GitHub Secrets」セクションから値を取得

### ステップ2: リポジトリ設定へアクセス
1. GitHubリポジトリを開く
2. `Settings` タブをクリック
3. 左サイドバーの `Secrets and variables` をクリック
4. `Actions` を選択

### ステップ3: 最初のSecretを追加
1. `New repository secret` ボタンをクリック
2. Name: `WIF_PROVIDER`
3. Value: setup スクリプトで出力された `WIF_PROVIDER` の値をコピー&ペースト
4. `Add secret` をクリック

### ステップ4: 2つ目のSecretを追加
1. 再度 `New repository secret` ボタンをクリック
2. Name: `WIF_SERVICE_ACCOUNT`
3. Value: setup スクリプトで出力された `WIF_SERVICE_ACCOUNT` の値をコピー&ペースト
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
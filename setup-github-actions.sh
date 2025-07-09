#!/bin/bash
# GitHub Actions用サービスアカウント作成スクリプト

set -e

# デバッグモード (引数に --debug を付けると詳細ログが出力される)
if [[ "$1" == "--debug" ]]; then
    set -x
fi

PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Google Cloud プロジェクトが設定されていません"
    echo "gcloud config set project YOUR_PROJECT_ID を実行してください"
    exit 1
fi

SA_NAME="github-actions-deploy"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 GitHub Actions用サービスアカウントを作成します"
echo "プロジェクト: $PROJECT_ID"
echo "サービスアカウント: $SA_EMAIL"
echo ""

# サービスアカウントの作成
echo "1. サービスアカウントを確認中..."
if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "   ✅ サービスアカウント $SA_EMAIL は既に存在します"
    echo "   既存のサービスアカウントを使用します"
else
    echo "   サービスアカウントを作成中..."
    gcloud iam service-accounts create $SA_NAME \
        --display-name="GitHub Actions Deploy Service Account" \
        --description="GitHub Actions用のCloud Runデプロイサービスアカウント" \
        --project=$PROJECT_ID
    echo "   ✅ サービスアカウント $SA_EMAIL を作成しました"
fi

# 必要な権限を付与
echo "2. 権限を確認・付与中..."
ROLES=(
    "roles/run.admin"
    "roles/cloudbuild.builds.builder"
    "roles/storage.admin"
    "roles/secretmanager.secretAccessor"
    "roles/iam.serviceAccountUser"
    "roles/artifactregistry.admin"
)

for role in "${ROLES[@]}"; do
    echo "   - $role を確認中..."
    if gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format="table(bindings.role,bindings.members)" --filter="bindings.members:serviceAccount:$SA_EMAIL AND bindings.role:$role" 2>/dev/null | grep -q "$role"; then
        echo "     ✅ 既に付与済み"
    else
        echo "     🔄 権限を付与中..."
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$role" \
            --quiet
        echo "     ✅ 権限を付与しました"
    fi
done

# サービスアカウントキーの作成
echo "3. サービスアカウントキーを作成中..."
KEY_FILE="github-actions-key.json"

# 既存のキーファイルを削除
if [ -f "$KEY_FILE" ]; then
    rm "$KEY_FILE"
    echo "   🗑️  既存のキーファイルを削除しました"
fi

# 新しいキーを作成
gcloud iam service-accounts keys create $KEY_FILE \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "   ✅ サービスアカウントキーを作成しました"
else
    echo "   ❌ サービスアカウントキーの作成に失敗しました"
    exit 1
fi

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "次のステップ:"
echo "1. GitHub リポジトリの Settings > Secrets and variables > Actions へ移動"
echo "2. New repository secret をクリック"
echo "3. Name: GCP_SA_KEY"
echo "4. Value: 以下の内容をコピー&ペースト"
echo ""
echo "=== サービスアカウントキー (GCP_SA_KEY) ==="
cat $KEY_FILE
echo ""
echo "=== ここまで ==="
echo ""
echo "⚠️  重要: このキーファイルは削除してください"
echo "rm $KEY_FILE"
echo ""
echo "📋 付与した権限:"
for role in "${ROLES[@]}"; do
    echo "   - $role"
done

echo ""
echo "🔍 トラブルシューティング:"
echo "  - エラーが発生した場合は、gcloud auth login でログインし直してください"
echo "  - 権限が不足している場合は、プロジェクトのオーナー権限が必要です"
echo "  - サービスアカウントを削除したい場合："
echo "    gcloud iam service-accounts delete $SA_EMAIL --project=$PROJECT_ID"
echo ""
echo "📚 詳細なセットアップ手順："
echo "  README_GITHUB_ACTIONS.md を参照してください"
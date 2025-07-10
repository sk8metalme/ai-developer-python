#!/bin/bash
# GitHub Actions用Workload Identity設定スクリプト

set -e

# デバッグモード
if [[ "$1" == "--debug" ]]; then
    set -x
fi

PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Google Cloud プロジェクトが設定されていません"
    echo "gcloud config set project YOUR_PROJECT_ID を実行してください"
    exit 1
fi

# プロジェクト番号を取得
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
if [ -z "$PROJECT_NUMBER" ]; then
    echo "❌ プロジェクト番号の取得に失敗しました"
    exit 1
fi

SA_NAME="github-actions-deploy"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
REPO_OWNER="sk8metalme"  # GitHubのオーナー名
REPO_NAME="ai-developer-python"  # リポジトリ名

echo "🚀 GitHub Actions用Workload Identity を設定します"
echo "プロジェクト: $PROJECT_ID ($PROJECT_NUMBER)"
echo "サービスアカウント: $SA_EMAIL"
echo "GitHubリポジトリ: $REPO_OWNER/$REPO_NAME"
echo ""

# 必要なAPIを有効化
echo "0. 必要なAPIを有効化中..."
APIS=(
    "iamcredentials.googleapis.com"
    "sts.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "secretmanager.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo "   - $api を有効化中..."
    gcloud services enable $api --project=$PROJECT_ID --quiet
done
echo "   ✅ APIを有効化しました"
echo ""

# Workload Identity Poolの作成
POOL_ID="github-actions-pool"
echo "1. Workload Identity Pool を作成中..."
if gcloud iam workload-identity-pools describe $POOL_ID --location="global" --project=$PROJECT_ID &>/dev/null; then
    echo "   ✅ Workload Identity Pool $POOL_ID は既に存在します"
else
    gcloud iam workload-identity-pools create $POOL_ID \
        --location="global" \
        --display-name="GitHub Actions Pool" \
        --description="GitHub Actions用のWorkload Identity Pool" \
        --project=$PROJECT_ID
    echo "   ✅ Workload Identity Pool $POOL_ID を作成しました"
fi

# Workload Identity Providerの作成
PROVIDER_ID="github-actions-provider"
echo "2. Workload Identity Provider を作成中..."
if gcloud iam workload-identity-pools providers describe $PROVIDER_ID --location="global" --workload-identity-pool=$POOL_ID --project=$PROJECT_ID &>/dev/null; then
    echo "   ✅ Workload Identity Provider $PROVIDER_ID は既に存在します"
else
    gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID \
        --location="global" \
        --workload-identity-pool=$POOL_ID \
        --display-name="GitHub Actions Provider" \
        --description="GitHub Actions用のOIDC Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
        --attribute-condition="assertion.repository_owner=='$REPO_OWNER'" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --project=$PROJECT_ID
    echo "   ✅ Workload Identity Provider $PROVIDER_ID を作成しました"
fi

# サービスアカウントの作成
echo "3. サービスアカウントを確認中..."
if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "   ✅ サービスアカウント $SA_EMAIL は既に存在します"
else
    gcloud iam service-accounts create $SA_NAME \
        --display-name="GitHub Actions Deploy Service Account" \
        --description="GitHub Actions用のCloud Runデプロイサービスアカウント" \
        --project=$PROJECT_ID
    echo "   ✅ サービスアカウント $SA_EMAIL を作成しました"
fi

# 権限の付与
echo "4. 権限を確認・付与中..."
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

# Workload Identity の関連付け
echo "5. Workload Identity の関連付け中..."
PRINCIPAL_SET="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/attribute.repository/$REPO_OWNER/$REPO_NAME"

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --role="roles/iam.workloadIdentityUser" \
    --member="$PRINCIPAL_SET" \
    --project=$PROJECT_ID \
    --quiet

echo "   ✅ Workload Identity を関連付けました"

# Workload Identity Provider の詳細取得
WIF_PROVIDER="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "次のステップ:"
echo "1. GitHub リポジトリの Settings > Secrets and variables > Actions へ移動"
echo "2. 以下の Secrets を追加してください:"
echo ""
echo "=== GitHub Secrets ==="
echo "Name: WIF_PROVIDER"
echo "Value: $WIF_PROVIDER"
echo ""
echo "Name: WIF_SERVICE_ACCOUNT"
echo "Value: $SA_EMAIL"
echo ""
echo "=== ここまで ==="
echo ""
echo "📋 付与した権限:"
for role in "${ROLES[@]}"; do
    echo "   - $role"
done

echo ""
echo "🔍 トラブルシューティング:"
echo "  - エラーが発生した場合は、gcloud auth login でログインし直してください"
echo "  - 権限が不足している場合は、プロジェクトのオーナー権限が必要です"
echo "  - Workload Identity Poolを削除したい場合："
echo "    gcloud iam workload-identity-pools delete $POOL_ID --location=global --project=$PROJECT_ID"
echo ""
echo "📚 詳細なセットアップ手順："
echo "  README_GITHUB_ACTIONS.md を参照してください"
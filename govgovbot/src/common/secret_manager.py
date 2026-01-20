"""Google Cloud Secret Manager クライアント

環境変数が設定されていない場合にSecret Managerから取得します。
"""

import os
from typing import Optional
from google.cloud import secretmanager


def get_secret(secret_id: str, project_id: Optional[str] = None) -> Optional[str]:
    """Secret Managerからシークレット値を取得する
    
    Args:
        secret_id: シークレットID
        project_id: プロジェクトID（未指定時は環境変数から取得）
    
    Returns:
        シークレット値、取得失敗時はNone
    """
    try:
        if not project_id:
            project_id = os.getenv("PROJECT_ID") or os.getenv("GCP_PROJECT_ID")
        
        if not project_id:
            return None
        
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"SECRET_MANAGER_ERROR: Failed to get {secret_id}: {e}")
        return None


def load_secrets_to_env() -> None:
    """Secret Managerから必要な認証情報を環境変数にロードする
    
    既に環境変数が設定されている場合はスキップします。
    """
    secret_mappings = {
        "X_API_KEY": "x-api-key",
        "X_API_SECRET": "x-api-secret",
        "X_ACCESS_TOKEN": "x-access-token",
        "X_ACCESS_TOKEN_SECRET": "x-access-token-secret",
        # 重要: X_BEARER_TOKENは必須（メンション取得に必要）
        # 詳細は docs/X_API_AUTHENTICATION.md を参照
        "X_BEARER_TOKEN": "x-bearer-token",
        "VERTEX_AI_SEARCH_DATA_STORE_ID": "vertex-ai-search-datastore-id",
        "RAG_CORPUS_RESOURCE_NAME": "rag-corpus-resource-name",
    }
    
    for env_var, secret_id in secret_mappings.items():
        # 既に環境変数が設定されていればスキップ
        if os.getenv(env_var):
            print(f"{env_var} already set in environment, skipping Secret Manager")
            continue
        
        # Secret Managerから取得
        value = get_secret(secret_id)
        if value:
            os.environ[env_var] = value
            print(f"Loaded {env_var} from Secret Manager")
        else:
            print(f"WARNING: Failed to load {env_var} from Secret Manager (secret_id: {secret_id})")


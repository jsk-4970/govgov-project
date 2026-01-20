# X (Twitter) API 認証ガイド

このドキュメントでは、govgovボットで使用しているX APIの認証方法と、重要な知見をまとめています。

## 📋 目次

- [必要な認証情報](#必要な認証情報)
- [認証方式の使い分け](#認証方式の使い分け)
- [重要な知見: Bearer Tokenは必須](#重要な知見-bearer-tokenは必須)
- [メンション取得の実装](#メンション取得の実装)
- [トラブルシューティング](#トラブルシューティング)

## 必要な認証情報

### 必須の認証情報（OAuth 1.0a）

以下の4つの認証情報は、ツイート投稿や基本的なAPI操作に必要です：

1. **API Key (Consumer Key)**
   - 環境変数: `X_API_KEY`
   - Secret Manager: `x-api-key`
   - X Developer Portalで取得

2. **API Secret (Consumer Secret)**
   - 環境変数: `X_API_SECRET`
   - Secret Manager: `x-api-secret`
   - X Developer Portalで取得

3. **Access Token**
   - 環境変数: `X_ACCESS_TOKEN`
   - Secret Manager: `x-access-token`
   - OAuth認証フローで取得

4. **Access Token Secret**
   - 環境変数: `X_ACCESS_TOKEN_SECRET`
   - Secret Manager: `x-access-token-secret`
   - OAuth認証フローで取得

### 必須の認証情報（Bearer Token）

5. **Bearer Token**
   - 環境変数: `X_BEARER_TOKEN`
   - Secret Manager: `x-bearer-token`
   - **重要: メンション取得には必須です（後述）**

## 認証方式の使い分け

### OAuth 1.0a（ユーザーコンテキスト）

**用途:**
- ツイート投稿 (`create_tweet`)
- 自分の情報取得 (`get_me`)
- ユーザー情報の取得

**使用箇所:**
- `src/phase2/twitter_poster.py` - ツイート投稿
- `src/phase2/twitter_listener.py` - 基本的なAPI操作

### Bearer Token（アプリ専用）

**用途:**
- メンション取得 (`/users/{user_id}/mentions`)
- 検索操作 (`search_recent_tweets`)
- 読み取り専用の操作

**使用箇所:**
- `src/phase2/twitter_listener.py` - メンション取得（優先的に使用）

## 重要な知見: Bearer Tokenは必須

### なぜBearer Tokenが必要なのか？

**問題:**
- OAuth 1.0aの認証情報（API Key, API Secret, Access Token, Access Token Secret）だけでは、`get_users_mentions()`エンドポイントにアクセスできない場合があります
- 特に、**FreeプランやBasicプランでは、`get_users_mentions()`が401 Unauthorizedエラーを返す**ことがあります

**解決策:**
- **Bearer Tokenを使った直接HTTPリクエスト**で、`/users/{user_id}/mentions`エンドポイントにアクセスする必要があります
- この方法なら、FreeプランやBasicプランでも動作します

### 実装の詳細

`src/phase2/twitter_listener.py`の`poll_mentions()`関数では、以下の優先順位でメンション取得を試みます：

1. **Bearer Token方式（優先）**
   ```python
   # Bearer Tokenを使って直接HTTPリクエスト
   url = f"https://api.twitter.com/2/users/{user_id}/mentions"
   headers = {"Authorization": f"Bearer {bearer_token}"}
   response = requests.get(url, headers=headers, params=params)
   ```

2. **Tweepyクライアント方式（フォールバック）**
   ```python
   # OAuth 1.0aでget_users_mentions()を試す
   resp = client.get_users_mentions(id=user_id, ...)
   ```

3. **検索API方式（最終フォールバック）**
   ```python
   # 検索クエリでメンションを探す
   query = f"@{handle} -from:{handle}"
   resp = client.search_recent_tweets(query=query, ...)
   ```

### 参考コード

以下のような直接HTTPリクエストの方法が、低いアクセスレベルでも動作します：

```javascript
// Node.jsの例（参考）
const response = await axios.get(
    `https://api.twitter.com/2/users/${MY_USER_ID}/mentions`,
    {
        headers: {
            'Authorization': `Bearer ${BEARER_TOKEN}`
        },
        params: {
            'max_results': 10,
            'tweet.fields': 'created_at,author_id,conversation_id'
        }
    }
);
```

## メンション取得の実装

### 現在の実装フロー

```
poll_mentions()
├─ Bearer Token方式を試行
│  ├─ 成功 → メンションを返す
│  └─ 失敗 → 次の方式へ
├─ Tweepy get_users_mentions()を試行
│  ├─ 成功 → メンションを返す
│  └─ 失敗 → 次の方式へ
└─ 検索API方式を試行
   └─ 成功/失敗に関わらず結果を返す
```

### コードの場所

- **メイン実装**: `src/phase2/twitter_listener.py` の `poll_mentions()` 関数（839行目〜）

## トラブルシューティング

### 401 Unauthorizedエラーが発生する場合

**症状:**
- `get_users_mentions()`で401エラー
- `search_recent_tweets()`で401エラー

**原因:**
- Bearer Tokenが設定されていない
- Bearer Tokenが無効になっている
- アクセスレベルが不足している

**解決策:**
1. Bearer TokenがSecret Managerに正しく保存されているか確認
2. X Developer PortalでBearer Tokenを再生成
3. Secret Managerを更新

### 403 Forbiddenエラーが発生する場合

**症状:**
- `mentions_timeline()`（v1.1 API）で403エラー

**原因:**
- v1.1 APIへのアクセス権限がない
- アクセスレベルが不足している

**解決策:**
- Bearer Token方式を使用する（既に実装済み）
- v1.1 APIは使用しない（フォールバックのみ）

### 認証情報が読み込まれない場合

**症状:**
- `Missing env: X_API_KEY, X_API_SECRET, ...` エラー

**原因:**
- Secret Managerから認証情報が読み込まれていない
- Cloud Runのサービスアカウントに権限がない

**解決策:**
1. Cloud Runのサービスアカウントを確認
   ```bash
   gcloud run services describe factcheck-bot --region=asia-northeast1 \
     --format="value(spec.template.spec.serviceAccountName)"
   ```

2. Secret Managerへのアクセス権限を確認
   ```bash
   gcloud projects get-iam-policy govgov-473916 \
     --flatten="bindings[].members" \
     --filter="bindings.members:factcheck-bot-sa@govgov-473916.iam.gserviceaccount.com"
   ```

3. サービスアカウントを正しく設定
   ```bash
   gcloud run services update factcheck-bot \
     --region=asia-northeast1 \
     --service-account=factcheck-bot-sa@govgov-473916.iam.gserviceaccount.com
   ```

## Secret Managerへの保存方法

### 認証情報の更新

```bash
# .envファイルからSecret Managerに更新
python3 << 'EOF'
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()

secrets = {
    "x-api-key": os.getenv("X_API_KEY"),
    "x-api-secret": os.getenv("X_API_SECRET"),
    "x-access-token": os.getenv("X_ACCESS_TOKEN"),
    "x-access-token-secret": os.getenv("X_ACCESS_TOKEN_SECRET"),
    "x-bearer-token": os.getenv("X_BEARER_TOKEN"),
}

project_id = "govgov-473916"

for secret_id, value in secrets.items():
    if not value:
        print(f"WARNING: {secret_id} is not set in .env")
        continue
    
    # シークレットの存在確認
    result = subprocess.run(
        ["gcloud", "secrets", "describe", secret_id, "--project", project_id],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        # シークレットが存在しない場合は作成
        subprocess.run(
            ["gcloud", "secrets", "create", secret_id, "--project", project_id],
            check=True
        )
    
    # 新しいバージョンを追加
    process = subprocess.Popen(
        ["gcloud", "secrets", "versions", "add", secret_id, "--project", project_id, "--data-file=-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=value)
    
    if process.returncode == 0:
        print(f"✓ Successfully updated {secret_id}")
    else:
        print(f"✗ Failed to update {secret_id}: {stderr}")
EOF
```

## まとめ

### 重要なポイント

1. **Bearer Tokenは必須**: メンション取得にはBearer Tokenが必要です
2. **直接HTTPリクエスト方式**: Tweepyの`get_users_mentions()`が失敗する場合、Bearer Tokenで直接HTTPリクエストを送る方法が有効です
3. **フォールバック処理**: 複数の方式を試すことで、異なるアクセスレベルでも動作します
4. **Secret Manager管理**: 認証情報はSecret Managerで管理し、Cloud Runから自動的に読み込まれます

### 参考リンク

- [X API Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [Tweepy Documentation](https://docs.tweepy.org/)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)

---

**最終更新**: 2025-11-13  
**作成者**: govgov開発チーム


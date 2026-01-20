# GCP手動セットアップガイド（gcloud CLI不使用）

**プロジェクトID**: `govgov-473916`

このガイドでは、gcloud CLIを使わずにGoogle Cloud Consoleのブラウザ画面から手動でセットアップする手順を説明します。

---

## ✅ 完了している作業

- [x] GCPプロジェクト作成（プロジェクトID: `govgov-473916`）
- [x] `.env`ファイルにプロジェクトIDを設定

## 📋 次のステップ

### ステップ1: 請求先アカウントの設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 画面上部でプロジェクト `govgov-473916` が選択されていることを確認
3. ナビゲーションメニュー（☰）→「お支払い」をクリック
4. 請求先アカウントをリンク（無料枠を使用する場合でも必要）

---

### ステップ2: 必要なAPIの有効化

以下のAPIを有効化します。

#### 2.1 Vertex AI API

1. [Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=govgov-473916) にアクセス
2. 「有効にする」をクリック
3. 有効化が完了するまで待機（数分かかる場合があります）

#### 2.2 Cloud Storage API

1. [Cloud Storage API](https://console.cloud.google.com/apis/library/storage.googleapis.com?project=govgov-473916) にアクセス
2. 「有効にする」をクリック

#### 2.3 Secret Manager API

1. [Secret Manager API](https://console.cloud.google.com/apis/library/secretmanager.googleapis.com?project=govgov-473916) にアクセス
2. 「有効にする」をクリック

#### 2.4 Discovery Engine API (Vertex AI Search用)

1. [Discovery Engine API](https://console.cloud.google.com/apis/library/discoveryengine.googleapis.com?project=govgov-473916) にアクセス
2. 「有効にする」をクリック

**確認方法**:
- [APIとサービス > ダッシュボード](https://console.cloud.google.com/apis/dashboard?project=govgov-473916) で有効化されたAPIを確認できます

---

### ステップ3: Cloud Storage バケットの作成

#### 3.1 バケット作成

1. [Cloud Storage](https://console.cloud.google.com/storage/browser?project=govgov-473916) にアクセス
2. 「バケットを作成」をクリック
3. 以下の設定で作成:

| 項目 | 設定値 |
|------|--------|
| バケット名 | `govgov-473916-data` （または他の一意な名前） |
| ロケーションタイプ | Region |
| ロケーション | `asia-northeast1` (Tokyo) |
| ストレージクラス | Standard |
| アクセス制御 | 均一 (Uniform) |
| 保護ツール | なし（プロトタイプなので） |

4. 「作成」をクリック

#### 3.2 .envファイルの更新

バケット名が `govgov-473916-data` と異なる場合、`.env`ファイルを更新:

```bash
GCS_BUCKET_NAME=your-actual-bucket-name
```

---

### ステップ4: Vertex AI Search のセットアップ

#### 4.1 Vertex AI Search コンソールへアクセス

1. [Vertex AI Search & Conversation](https://console.cloud.google.com/gen-app-builder/engines?project=govgov-473916) にアクセス
2. 初回の場合、利用規約に同意を求められるので同意

#### 4.2 検索アプリの作成

1. 「アプリを作成」または「検索アプリを作成」をクリック
2. 以下の設定で作成:

**基本設定**:
- **アプリ名**: `factcheck-search-app`
- **会社名**: `Government Factcheck` （任意）
- **検索機能**: 「検索」を選択
- **コンテンツタイプ**: 「非構造化データ」を選択（PDFファイル対応のため）

**詳細設定**:
- **リージョン**: `asia-northeast1` (Tokyo)
- **Search with Google の機能**: 「Generic」を選択

3. 「続行」をクリック

#### 4.3 データストアの作成

1. 「新しいデータストアを作成」を選択
2. 以下の設定で作成:

| 項目 | 設定値 |
|------|--------|
| データソース | Cloud Storage |
| Cloud Storageのパス | `gs://govgov-473916-data/` |
| データストア名 | `review-data-store` |
| リージョン | `global` |

3. 「作成」をクリック

**注意**: データストアは作成されますが、まだデータがないため空の状態です。

#### 4.4 データストアIDとエンジンIDの取得

作成後、以下の方法でIDを確認します:

**データストアID**:
1. [Vertex AI Search > データストア](https://console.cloud.google.com/gen-app-builder/data-stores?project=govgov-473916) にアクセス
2. `review-data-store` をクリック
3. ページ上部の「データストアID」をコピー
   - 形式: `projects/PROJECT_NUMBER/locations/global/collections/default_collection/dataStores/DATA_STORE_ID`

**エンジンID（サーチアプリID）**:
1. [Vertex AI Search > アプリ](https://console.cloud.google.com/gen-app-builder/engines?project=govgov-473916) にアクセス
2. `factcheck-search-app` をクリック
3. ページ上部の「アプリID」をコピー
   - 形式: `projects/PROJECT_NUMBER/locations/global/collections/default_collection/engines/ENGINE_ID`

#### 4.5 .envファイルの更新

取得したIDを `.env` ファイルに設定:

```bash
VERTEX_AI_SEARCH_DATASTORE_ID=projects/123456789/locations/global/collections/default_collection/dataStores/review-data-store_1234567890
VERTEX_AI_SEARCH_ENGINE_ID=projects/123456789/locations/global/collections/default_collection/engines/factcheck-search-app_1234567890
```

---

### ステップ5: ローカル開発用の認証設定

gcloud CLIのインストールが完了したら実行します（後回しでもOK）:

```bash
# gcloudにログイン
gcloud auth login

# アプリケーションデフォルト認証
gcloud auth application-default login

# プロジェクトを設定
gcloud config set project govgov-473916
```

**gcloud CLIがまだインストールされていない場合**:
- ローカル開発は一旦スキップ
- GCPコンソールからの操作のみで進める
- または、サービスアカウントキーを使用（セキュリティリスクあり、推奨しない）

---

### ステップ6: サービスアカウントの作成（Cloud Run用）

#### 6.1 サービスアカウント作成

1. [IAMと管理 > サービスアカウント](https://console.cloud.google.com/iam-admin/serviceaccounts?project=govgov-473916) にアクセス
2. 「サービスアカウントを作成」をクリック
3. 以下を入力:

| 項目 | 設定値 |
|------|--------|
| サービスアカウント名 | `factcheck-bot-sa` |
| サービスアカウントID | `factcheck-bot-sa` |
| 説明 | `Service account for Factcheck Bot on Cloud Run` |

4. 「作成して続行」をクリック

#### 6.2 権限の付与

以下のロールを付与:

1. 「ロールを選択」をクリックして、以下を追加:
   - `Vertex AI ユーザー` (roles/aiplatform.user)
   - `ストレージ オブジェクト閲覧者` (roles/storage.objectViewer)
   - `Secret Manager のシークレット アクセサー` (roles/secretmanager.secretAccessor)

2. 「続行」→「完了」をクリック

---

## 📝 セットアップ完了チェックリスト

以下をすべて完了したか確認してください:

- [ ] 請求先アカウントのリンク
- [ ] Vertex AI API の有効化
- [ ] Cloud Storage API の有効化
- [ ] Secret Manager API の有効化
- [ ] Discovery Engine API の有効化
- [ ] Cloud Storage バケット `govgov-473916-data` の作成
- [ ] Vertex AI Search アプリ `factcheck-search-app` の作成
- [ ] データストア `review-data-store` の作成
- [ ] データストアIDを `.env` に設定
- [ ] エンジンIDを `.env` に設定
- [ ] サービスアカウント `factcheck-bot-sa` の作成
- [ ] サービスアカウントへの権限付与

---

## 🔧 トラブルシューティング

### APIが有効化できない
- 請求先アカウントがリンクされているか確認
- プロジェクト選択が正しいか確認（`govgov-473916`）

### バケット名が使えない
- バケット名はグローバルで一意である必要があります
- `govgov-473916-data-YYYYMMDD` のように日付を付けるなど工夫してください

### Vertex AI Search が見つからない
- Discovery Engine API が有効化されているか確認
- ブラウザのキャッシュをクリアしてリロード

---

## 次のステップ

セットアップが完了したら:

1. **データの準備**: 行政事業レビューデータを収集
2. **データのアップロード**: Cloud Storage バケットにアップロード
3. **Vertex AI Searchへのインポート**: データストアにインポート
4. **機能実装**: フェーズ1の機能（F-01, F-02, F-03）を実装

詳細は [README.md](../README.md) を参照してください。

---

## 参考リンク

- [Google Cloud Console - プロジェクト govgov-473916](https://console.cloud.google.com/?project=govgov-473916)
- [Cloud Storage バケット一覧](https://console.cloud.google.com/storage/browser?project=govgov-473916)
- [Vertex AI Search コンソール](https://console.cloud.google.com/gen-app-builder/engines?project=govgov-473916)
- [APIとサービス](https://console.cloud.google.com/apis/dashboard?project=govgov-473916)
- [IAMと管理](https://console.cloud.google.com/iam-admin/iam?project=govgov-473916)

# Vertex AI Search セットアップ手順

**今すぐ実施する作業**

プロジェクトID: `govgov-473916`

---

## 📋 セットアップ手順（ブラウザで実施）

### ステップ1: Vertex AI Search コンソールにアクセス

**リンク**: [Vertex AI Search コンソール](https://console.cloud.google.com/gen-app-builder/engines?project=govgov-473916)

ブラウザで上記リンクを開いてください。

---

### ステップ2: 検索アプリを作成

1. **「アプリを作成」または「検索アプリを作成」をクリック**

2. **基本設定を入力**:

   | 項目 | 入力値 |
   |------|--------|
   | アプリ名 | `factcheck-search-app` |
   | 会社名 | `Government Factcheck` （任意） |
   | アプリタイプ | **検索** を選択 |
   | コンテンツタイプ | **非構造化データ** を選択 |

3. **詳細設定**:

   | 項目 | 入力値 |
   |------|--------|
   | リージョン | `asia-northeast1` (Tokyo) |
   | Search with Google の機能 | **Generic** を選択 |

4. **「続行」をクリック**

---

### ステップ3: データストアを作成

1. **「新しいデータストアを作成」を選択**

2. **データソースの設定**:

   | 項目 | 入力値 |
   |------|--------|
   | データソース | **Cloud Storage** を選択 |
   | Cloud Storageのパス | `gs://govgov-473916-data/` |
   | データストア名 | `review-data-store` |
   | リージョン | `global` |

3. **「作成」をクリック**

   ⚠️ データストアは作成されますが、まだデータが空の状態です（後でデータをアップロードします）

---

### ステップ4: データストアIDとエンジンIDを取得

作成完了後、IDを取得します。

#### 4-1. データストアIDの取得

1. [Vertex AI Search > データストア](https://console.cloud.google.com/gen-app-builder/data-stores?project=govgov-473916) にアクセス

2. `review-data-store` をクリック

3. ページ上部の **「データストアID」** をコピー

   **形式例**:
   ```
   projects/335117605715/locations/global/collections/default_collection/dataStores/review-data-store_1234567890
   ```

   📋 **コピーしたIDをメモしてください**

#### 4-2. エンジンID（サーチアプリID）の取得

1. [Vertex AI Search > アプリ](https://console.cloud.google.com/gen-app-builder/engines?project=govgov-473916) にアクセス

2. `factcheck-search-app` をクリック

3. ページ上部の **「アプリID」** をコピー

   **形式例**:
   ```
   projects/335117605715/locations/global/collections/default_collection/engines/factcheck-search-app_1234567890
   ```

   📋 **コピーしたIDをメモしてください**

---

### ステップ5: .env ファイルを更新

取得した2つのIDを `.env` ファイルに設定します。

**コマンド**:
```bash
# エディタで .env を開く
nano .env

# または
code .env
```

**更新内容**:

以下の2行を、取得した実際のIDに置き換えてください:

```bash
# 変更前
VERTEX_AI_SEARCH_DATASTORE_ID=your-datastore-id
VERTEX_AI_SEARCH_ENGINE_ID=your-search-engine-id

# 変更後（例）
VERTEX_AI_SEARCH_DATASTORE_ID=projects/335117605715/locations/global/collections/default_collection/dataStores/review-data-store_1234567890
VERTEX_AI_SEARCH_ENGINE_ID=projects/335117605715/locations/global/collections/default_collection/engines/factcheck-search-app_1234567890
```

**保存して閉じる**

---

## ✅ 完了確認

以下のコマンドで、.envファイルが正しく設定されているか確認:

```bash
cat .env | grep VERTEX_AI_SEARCH
```

**出力例**:
```
VERTEX_AI_SEARCH_DATASTORE_ID=projects/335117605715/...
VERTEX_AI_SEARCH_ENGINE_ID=projects/335117605715/...
```

両方とも `projects/` で始まる長いIDが設定されていればOKです。

---

## 🎯 次のステップ

Vertex AI Searchのセットアップが完了したら:

1. **サンプルデータの準備**
   - 行政事業レビューのPDFを数件ダウンロード
   - または、テスト用のサンプルファイルを作成

2. **フェーズ1の機能実装開始**
   - F-01: ナレッジソース構築（データアップロード）
   - F-03: ファクトチェック実行（検索と回答生成）
   - F-02: CLIインターフェース（テスト用UI）

---

## 🚨 トラブルシューティング

### Vertex AI Searchが見つからない

- Discovery Engine API が有効化されているか確認
- ブラウザのキャッシュをクリアしてリロード
- プロジェクト `govgov-473916` が選択されているか確認

### データストア作成時にエラー

- Cloud Storage バケット `govgov-473916-data` が存在するか確認:
  ```bash
  gcloud storage buckets describe gs://govgov-473916-data
  ```

### IDが見つからない

- データストアまたはアプリの詳細ページを開く
- ページ上部に表示されるID文字列をコピー
- "Copy resource name" のようなボタンがあればそれを使用

---

**このセットアップが完了したら教えてください！次の実装ステップに進みます。**

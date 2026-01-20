# Vertex AI Search セットアップ完了レポート

## ✅ セットアップ状況

### 1. データストア情報

| 項目 | 値 |
|------|-----|
| プロジェクトID | `govgov-473916` |
| データストアID | `datastore-govgov_1759561195262` |
| ロケーション | `global` |
| データソース | Cloud Storage (`gs://govgov-473916-data/`) |

### 2. 実装完了済みコンポーネント

#### ✅ 共通モジュール

- **`src/common/vertex_search_client.py`**: Vertex AI Searchクライアント
  - エンドポイント自動選択（global/リージョナル）
  - リトライ処理（tenacity使用）
  - 回答生成とソース抽出
  - エラーハンドリング

- **`src/common/config.py`**: 設定管理
  - `VertexAISearchConfig`: Vertex AI Search用設定クラス追加
  - 環境変数からの自動読み込み
  - オプショナルな設定サポート（require_vertex_search）

#### ✅ CLI ツール

- **`src/phase1/fact_check_cli.py`**: ファクトチェックCLIツール
  - コマンドライン引数対応
  - 要件定義に準拠した出力フォーマット
  - Vertex AI Search統合

#### ✅ 環境設定

- **`.env.example`**: 環境変数テンプレート更新
  - `VERTEX_AI_SEARCH_DATA_STORE_ID`
  - `VERTEX_AI_SEARCH_LOCATION`
  - 適切なデフォルト値設定

- **`requirements.txt`**: 依存関係追加
  - `google-cloud-discoveryengine`

### 3. 技術的な解決事項

#### 問題1: エンドポイント不一致エラー
**エラー**: `Incorrect API endpoint used. The current endpoint can only serve traffic from "global" region, but got "asia-northeast1" region`

**根本原因**:
- データストアは`global`リージョンに存在
- クライアント初期化時にロケーション固有のエンドポイント指定が必要

**解決策**:
```python
# ロケーションに応じたAPIエンドポイントを設定
if location == "global":
    api_endpoint = "discoveryengine.googleapis.com"
else:
    api_endpoint = f"{location}-discoveryengine.googleapis.com"

# クライアント初期化
self.client = discoveryengine.SearchServiceClient(
    client_options={"api_endpoint": api_endpoint}
)
```

#### 問題2: モデルバージョン指定エラー
**エラー**: `Invalid version in model spec for summary: gemini-1.5-flash-001/answer_gen/v1`

**解決策**: モデルバージョン指定を削除し、デフォルトを使用

### 4. 現在の課題

#### ⚠️ データインポートの問題

**症状**:
- 検索実行は成功するが、意味のある回答が生成されない
- 「検索語句の要約を生成できませんでした」というメッセージ

**原因分析**:
```bash
# ドキュメント確認
$ python3 << 'EOF'
# ... list documents ...
# Data keys: []  ← データが空
EOF
```

**データストア状況**:
- ドキュメント数: 5件存在
- データ内容: 空（`Data keys: []`）
- JSONLファイル: GCSバケットに存在するが、正しくインポートされていない

**次のステップ**:
1. JSONLファイルのスキーマをVertex AI Search用に修正
2. データの再インポート
3. インデックスの再構築

### 5. 使用方法

#### 環境変数設定（.env）

```bash
# Google Cloud Platform
PROJECT_ID=govgov-473916
LOCATION=global

# Vertex AI Search
VERTEX_AI_SEARCH_DATA_STORE_ID=datastore-govgov_1759561195262
VERTEX_AI_SEARCH_LOCATION=global
```

#### CLIツールの実行

```bash
# 基本的な使用方法
python src/phase1/fact_check_cli.py "質問文をここに入力"

# 例
python src/phase1/fact_check_cli.py "デジタル庁の予算について教えてください"
```

#### プログラムからの使用

```python
from src.common.vertex_search_client import VertexAISearchClient

# クライアント初期化
client = VertexAISearchClient(
    project_id="govgov-473916",
    location="global",
    data_store_id="datastore-govgov_1759561195262"
)

# 検索実行
result = client.search(
    query="デジタル庁の予算について",
    max_results=5
)

print(result["summary"])  # 生成された回答
print(result["sources"])  # 参照元リスト
```

### 6. 今後の開発に向けて

#### すぐに実施すべきこと

1. **データインポートの修正**
   - JSONLスキーマの確認と修正
   - Vertex AI Search用のメタデータフィールド追加
   - 再インポートの実行

2. **テストの追加**
   - `tests/common/test_vertex_search_client.py`
   - モック使用した単体テスト
   - エラーケースのテスト

#### 推奨される改善

1. **キャッシュ機能の追加**
   - 同じ質問への繰り返しクエリを削減
   - コスト最適化

2. **ロギングの強化**
   - 構造化ログ（JSON形式）への移行
   - Cloud Logging統合

3. **パフォーマンス監視**
   - レスポンスタイムの計測
   - API呼び出し回数の追跡

### 7. 参考情報

#### 関連ドキュメント

- [Vertex AI Search公式ドキュメント](https://cloud.google.com/generative-ai-app-builder/docs)
- [Discovery Engine Python Client](https://cloud.google.com/python/docs/reference/discoveryengine/latest)
- [CLAUDE.md](../CLAUDE.md) - プロジェクト設計ルール

#### トラブルシューティング

**Q: データストアIDの確認方法は？**
```bash
python3 << 'EOF'
from google.cloud import discoveryengine_v1beta as discoveryengine
client = discoveryengine_v1beta.DataStoreServiceClient(
    client_options={"api_endpoint": "discoveryengine.googleapis.com"}
)
parent = "projects/govgov-473916/locations/global/collections/default_collection"
for ds in client.list_data_stores(parent=parent):
    print(f"Name: {ds.name}")
    print(f"Display Name: {ds.display_name}")
EOF
```

**Q: エンドポイントエラーが出る場合**
- ロケーションが正しいか確認（`global` vs リージョン）
- クライアント初期化で`client_options`が設定されているか確認

**Q: 回答が生成されない場合**
- データストアにデータがインポートされているか確認
- インデックスが構築されているか確認（GCPコンソール）
- データのスキーマが正しいか確認

---

**更新日**: 2025-10-07
**ステータス**: 基盤実装完了、データインポート要対応

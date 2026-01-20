# Vertex AI Search vs RAG Engine 比較ドキュメント

## 概要

このプロジェクトには2つの異なる検索・回答生成クライアントが実装されています。

## クライアント比較

| 項目 | Vertex AI Search | Vertex AI RAG Engine |
|------|------------------|---------------------|
| **実装ファイル** | `src/common/vertex_search_client.py` | `src/common/rag_client.py` |
| **技術** | Discovery Engine (Search) | RAG Engine |
| **クラス名** | `VertexAISearchClient` | `VertexAIRAGClient` |
| **メソッド名** | `search()` | `query()` |
| **使用API** | `google-cloud-discoveryengine` | `google-cloud-aiplatform` |
| **データソース** | データストア | RAGコーパス |
| **現在の状態** | ✅ 実装完了、テスト済み | ⚠️ 実装済み、未テスト |

## 使い分け

### Vertex AI Search を使う場合

**適している用途**:
- 大量の非構造化データ（PDF、HTMLなど）の検索
- GUIでのデータストア管理が必要
- 回答生成付き検索（RAG）が必要
- **現在のプロジェクトではこちらを使用**

**メリット**:
- GUIでのデータ管理が簡単
- 自動的なインデックス構築
- 多様なデータソース対応

**デメリット**:
- 設定が複雑
- エンドポイント管理が必要

### Vertex AI RAG Engine を使う場合

**適している用途**:
- プログラマティックなRAG実装
- カスタマイズ可能な検索・生成プロセス
- 細かい制御が必要な場合

**メリット**:
- プログラマティックな制御
- 柔軟なプロンプト設定

**デメリット**:
- コーパス管理が複雑
- 現時点で未実装の機能が多い

## インターフェースの統一

将来的な統合のため、共通インターフェースを定義します。

### 共通インターフェース（案）

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseSearchClient(ABC):
    """検索・回答生成クライアントの基底クラス"""

    @abstractmethod
    def search(self, query: str, **kwargs) -> dict[str, Any]:
        """
        検索を実行し、回答を生成

        Args:
            query: 検索クエリ
            **kwargs: 実装固有のオプション

        Returns:
            {
                "answer": "生成された回答",
                "sources": ["参照元1", "参照元2", ...],
                "metadata": {...}  # 実装固有のメタデータ
            }
        """
        pass
```

### 実装クラスへの適用（将来）

```python
# Vertex AI Search版
class VertexAISearchClient(BaseSearchClient):
    def search(self, query: str, max_results: int = 5) -> dict[str, Any]:
        # ... 実装 ...
        return {
            "answer": summary,
            "sources": sources,
            "metadata": {"results": results}
        }

# RAG Engine版
class VertexAIRAGClient(BaseSearchClient):
    def search(self, query: str, similarity_top_k: int = 5) -> dict[str, Any]:
        # queryメソッドをsearchにリネーム
        result = self.query(query, similarity_top_k)
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "metadata": {"contexts": result["contexts"]}
        }
```

## 現在の推奨事項

### フェーズ1（現在）

**推奨**: `VertexAISearchClient` を使用

理由:
1. データストアが既にセットアップ済み
2. テスト済みで動作確認済み
3. GUI管理が可能

### フェーズ2以降

**検討事項**:
1. パフォーマンス比較
2. コスト比較
3. 機能要件に応じた選択

## マイグレーションパス

将来的にRAG Engineに移行する場合:

1. **BaseSearchClient実装**
   - 共通インターフェース定義
   - 両クライアントで実装

2. **アダプターパターン適用**
   ```python
   # 使用側のコード変更不要
   client: BaseSearchClient = get_search_client()  # 設定から取得
   result = client.search(query)
   ```

3. **段階的移行**
   - テスト環境でRAG Engineテスト
   - パフォーマンス・コスト比較
   - 本番環境へ移行

## 設定例

### Vertex AI Search（現在使用中）

```python
# .env
VERTEX_AI_SEARCH_DATA_STORE_ID=datastore-govgov_1759561195262
VERTEX_AI_SEARCH_LOCATION=global

# コード
from src.common.vertex_search_client import VertexAISearchClient

client = VertexAISearchClient(
    project_id=config.gcp.project_id,
    location=config.vertex_search.location,
    data_store_id=config.vertex_search.data_store_id
)
result = client.search(query="質問文")
```

### Vertex AI RAG Engine（将来の選択肢）

```python
# .env
RAG_CORPUS_ID=your-corpus-id
LOCATION=asia-northeast1

# コード
from src.common.rag_client import VertexAIRAGClient

client = VertexAIRAGClient(
    project_id=config.gcp.project_id,
    location=config.gcp.location,
    corpus_id=config.rag.corpus_id
)
result = client.query(question="質問文")
```

## まとめ

- **現在**: Vertex AI Search（Discovery Engine）を使用
- **将来**: 要件に応じてRAG Engineも検討可能
- **設計**: 共通インターフェースで将来の切り替えに対応

---

**最終更新**: 2025-10-07

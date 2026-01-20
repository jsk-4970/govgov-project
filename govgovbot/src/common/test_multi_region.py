"""マルチリージョンフェイルオーバー機能のテスト

Vertex AI RAG Engineのマルチリージョンフェイルオーバー機能をテストします。
"""

import os
import logging
from dotenv import load_dotenv
from vertex_rag_client import VertexAIRAGClient, VertexAIRAGError

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_multi_region_initialization():
    """マルチリージョン初期化のテスト"""
    logger.info("=" * 80)
    logger.info("Test 1: マルチリージョン初期化テスト")
    logger.info("=" * 80)

    load_dotenv()

    project_id = os.getenv("PROJECT_ID")
    rag_corpus_resource_name = os.getenv("RAG_CORPUS_RESOURCE_NAME")
    rag_location = os.getenv("RAG_LOCATION", "us-east4")

    if not project_id or not rag_corpus_resource_name:
        logger.error("PROJECT_ID or RAG_CORPUS_RESOURCE_NAME is not set")
        return False

    try:
        # マルチリージョン有効で初期化
        client = VertexAIRAGClient(
            project_id=project_id,
            location=rag_location,
            rag_corpus_resource_name=rag_corpus_resource_name,
            model_name="gemini-2.0-flash-exp",
            enable_multi_region=True,
        )

        logger.info(f"✓ マルチリージョン有効で初期化成功")
        logger.info(f"  - プライマリリージョン: {client.primary_location}")
        logger.info(f"  - 利用可能リージョン数: {len(client.available_regions)}")
        logger.info(f"  - 現在のリージョン: {client.available_regions[client.current_region_index]}")

        # マルチリージョン無効で初期化
        client_single = VertexAIRAGClient(
            project_id=project_id,
            location=rag_location,
            rag_corpus_resource_name=rag_corpus_resource_name,
            model_name="gemini-2.0-flash-exp",
            enable_multi_region=False,
        )

        logger.info(f"✓ マルチリージョン無効で初期化成功")
        logger.info(f"  - 利用可能リージョン数: {len(client_single.available_regions)}")

        return True

    except Exception as e:
        logger.error(f"✗ 初期化エラー: {e}", exc_info=True)
        return False


def test_simple_query():
    """シンプルなクエリテスト"""
    logger.info("=" * 80)
    logger.info("Test 2: シンプルなクエリテスト")
    logger.info("=" * 80)

    load_dotenv()

    project_id = os.getenv("PROJECT_ID")
    rag_corpus_resource_name = os.getenv("RAG_CORPUS_RESOURCE_NAME")
    rag_location = os.getenv("RAG_LOCATION", "us-east4")

    if not project_id or not rag_corpus_resource_name:
        logger.error("PROJECT_ID or RAG_CORPUS_RESOURCE_NAME is not set")
        return False

    try:
        client = VertexAIRAGClient(
            project_id=project_id,
            location=rag_location,
            rag_corpus_resource_name=rag_corpus_resource_name,
            model_name="gemini-2.0-flash-exp",
            enable_multi_region=True,
        )

        logger.info("クエリを実行中...")
        result = client.generate_answer(query="行政事業レビューについて簡単に説明してください")

        logger.info(f"✓ クエリ成功")
        logger.info(f"  - ステータス: {result.get('status')}")
        logger.info(f"  - 回答長: {len(result.get('answer', ''))}")
        logger.info(f"  - finish_reason: {result.get('finish_reason')}")
        logger.info(f"  - truncated: {result.get('truncated')}")
        logger.info(f"  - blocked: {result.get('blocked')}")

        if result.get('answer'):
            logger.info(f"  - 回答プレビュー: {result['answer'][:200]}...")

        return True

    except VertexAIRAGError as e:
        logger.error(f"✗ RAGエラー: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ 予期しないエラー: {e}", exc_info=True)
        return False


def test_region_switching_simulation():
    """リージョン切り替えのシミュレーションテスト"""
    logger.info("=" * 80)
    logger.info("Test 3: リージョン切り替えシミュレーション")
    logger.info("=" * 80)

    load_dotenv()

    project_id = os.getenv("PROJECT_ID")
    rag_corpus_resource_name = os.getenv("RAG_CORPUS_RESOURCE_NAME")
    rag_location = os.getenv("RAG_LOCATION", "us-east4")

    if not project_id or not rag_corpus_resource_name:
        logger.error("PROJECT_ID or RAG_CORPUS_RESOURCE_NAME is not set")
        return False

    try:
        client = VertexAIRAGClient(
            project_id=project_id,
            location=rag_location,
            rag_corpus_resource_name=rag_corpus_resource_name,
            model_name="gemini-2.0-flash-exp",
            enable_multi_region=True,
        )

        logger.info(f"初期リージョン: {client.available_regions[client.current_region_index]}")

        # 次のリージョンに切り替え
        logger.info("次のリージョンに切り替え中...")
        success = client._switch_to_next_region()

        if success:
            logger.info(f"✓ リージョン切り替え成功")
            logger.info(f"  - 現在のリージョン: {client.available_regions[client.current_region_index]}")
            logger.info(f"  - インデックス: {client.current_region_index}/{len(client.available_regions)-1}")
        else:
            logger.warning("✗ リージョン切り替え失敗（全リージョン試行済み）")

        # プライマリリージョンに復帰
        logger.info("プライマリリージョンに復帰中...")
        client._reset_to_primary_region()
        logger.info(f"✓ プライマリリージョンに復帰: {client.available_regions[client.current_region_index]}")

        return True

    except Exception as e:
        logger.error(f"✗ エラー: {e}", exc_info=True)
        return False


def main():
    """全テストを実行"""
    logger.info("\n" + "=" * 80)
    logger.info("マルチリージョンフェイルオーバー機能テスト開始")
    logger.info("=" * 80 + "\n")

    results = []

    # Test 1: 初期化テスト
    results.append(("初期化テスト", test_multi_region_initialization()))

    # Test 2: シンプルなクエリテスト
    results.append(("クエリテスト", test_simple_query()))

    # Test 3: リージョン切り替えシミュレーション
    results.append(("リージョン切り替えテスト", test_region_switching_simulation()))

    # 結果サマリー
    logger.info("\n" + "=" * 80)
    logger.info("テスト結果サマリー")
    logger.info("=" * 80)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, result in results if result)

    logger.info(f"\n合計: {passed}/{total} テスト成功")
    logger.info("=" * 80 + "\n")

    return all(result for _, result in results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

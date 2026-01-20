"""Vertex AI RAG Engine テストスクリプト

ローカル環境でRAG Engineの動作を確認するためのスクリプトです。
"""

import os
import sys
import logging
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.common.config import AppConfig
from src.common.rag_client import VertexAIRAGClient
from src.common.disclaimer import add_disclaimer

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """RAG Engineのローカルテスト"""
    print("=" * 80)
    print("Vertex AI RAG Engine テスト")
    print("=" * 80)
    print()

    # 環境変数の読み込み
    load_dotenv()
    logger.info("環境変数を読み込みました")

    try:
        # 設定の読み込み
        config = AppConfig.from_env()
        logger.info(f"設定を読み込みました: project={config.gcp.project_id}")

        # RAGクライアントの初期化
        client = VertexAIRAGClient(
            project_id=config.gcp.project_id,
            location=config.gcp.location,
            corpus_id=config.rag.corpus_id,
            model_name=config.rag.model_name
        )
        logger.info("RAGクライアントを初期化しました")

        # テスト質問
        test_questions = [
            "防衛省の2023年度の主要な事業について教えてください",
            "教育関連の予算はどのくらいですか？",
            "インフラ整備に関する事業レビューの結果は？"
        ]

        for i, question in enumerate(test_questions, 1):
            print(f"\n{'=' * 80}")
            print(f"質問 {i}/{len(test_questions)}: {question}")
            print(f"{'=' * 80}")

            try:
                # RAG検索 + 回答生成
                result = client.query(
                    question=question,
                    similarity_top_k=config.rag.similarity_top_k,
                    temperature=config.rag.temperature,
                    max_output_tokens=config.rag.max_output_tokens
                )

                # 免責事項を付与
                final_answer = add_disclaimer(
                    answer=result["answer"],
                    sources=result["sources"]
                )

                print(final_answer)
                print(f"\n[デバッグ情報]")
                print(f"  - 検索された文脈数: {len(result['contexts'])}")
                print(f"  - 参照元数: {len(result['sources'])}")

            except Exception as e:
                logger.error(f"質問 {i} の処理中にエラーが発生しました: {str(e)}")
                print(f"\n❌ エラーが発生しました: {str(e)}")

        print(f"\n{'=' * 80}")
        print("テスト完了")
        print(f"{'=' * 80}")

    except ValueError as e:
        logger.error(f"設定エラー: {str(e)}")
        print(f"\n❌ 設定エラー: {str(e)}")
        print("\n.envファイルに以下の環境変数が設定されているか確認してください:")
        print("  - PROJECT_ID")
        print("  - LOCATION")
        print("  - BUCKET_NAME")
        print("  - RAG_CORPUS_ID")
        sys.exit(1)

    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}", exc_info=True)
        print(f"\n❌ 予期しないエラー: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

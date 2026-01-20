#!/usr/bin/env python3
"""Vertex AI RAG コーパス セットアップスクリプト

RAGコーパスの作成とデータインポートを実行します。
"""

import os
import sys
import logging
from dotenv import load_dotenv
from google.cloud import aiplatform
from google.cloud.aiplatform import rag

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_rag_corpus(
    project_id: str,
    location: str,
    display_name: str = "行政事業レビューRAGコーパス",
    description: str = "行政事業レビューシート2023年度データ"
) -> str:
    """
    RAGコーパスを作成する

    Args:
        project_id: GCPプロジェクトID
        location: リージョン
        display_name: コーパスの表示名
        description: コーパスの説明

    Returns:
        作成されたコーパスのID
    """
    logger.info(f"RAGコーパスを作成しています: {display_name}")

    aiplatform.init(project=project_id, location=location)

    # RAGコーパスの作成
    corpus = rag.create_corpus(
        display_name=display_name,
        description=description,
    )

    corpus_id = corpus.name.split('/')[-1]
    logger.info(f"✅ RAGコーパスを作成しました: {corpus_id}")
    logger.info(f"   フルネーム: {corpus.name}")

    return corpus_id


def import_files_to_corpus(
    project_id: str,
    location: str,
    corpus_id: str,
    source_uris: list[str],
    chunk_size: int = 512,
    chunk_overlap: int = 50
):
    """
    RAGコーパスにファイルをインポートする

    Args:
        project_id: GCPプロジェクトID
        location: リージョン
        corpus_id: コーパスID
        source_uris: Cloud StorageのURIリスト
        chunk_size: テキストチャンクのサイズ（トークン数）
        chunk_overlap: チャンク間のオーバーラップ（トークン数）
    """
    logger.info(f"ファイルをインポートしています: {source_uris}")

    aiplatform.init(project=project_id, location=location)

    # コーパスの取得
    corpus_name = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"

    # ファイルのインポート
    response = rag.import_files(
        corpus_name=corpus_name,
        paths=source_uris,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    logger.info(f"✅ ファイルのインポートが完了しました")
    logger.info(f"   インポートされたファイル数: {len(source_uris)}")
    logger.info(f"   チャンクサイズ: {chunk_size} トークン")
    logger.info(f"   チャンクオーバーラップ: {chunk_overlap} トークン")

    return response


def main():
    """メイン処理"""
    print("=" * 80)
    print("Vertex AI RAG コーパス セットアップ")
    print("=" * 80)
    print()

    # 環境変数の読み込み
    load_dotenv()

    # 設定の取得
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION", "asia-northeast1")
    bucket_name = os.getenv("BUCKET_NAME")

    if not project_id:
        logger.error("PROJECT_ID 環境変数が設定されていません")
        sys.exit(1)

    if not bucket_name:
        logger.error("BUCKET_NAME 環境変数が設定されていません")
        sys.exit(1)

    logger.info(f"プロジェクトID: {project_id}")
    logger.info(f"リージョン: {location}")
    logger.info(f"バケット名: {bucket_name}")

    try:
        # ステップ1: RAGコーパスの作成
        print("\n[ステップ 1/2] RAGコーパスを作成します...")
        corpus_id = create_rag_corpus(
            project_id=project_id,
            location=location
        )

        # ステップ2: データのインポート
        print("\n[ステップ 2/2] データをインポートします...")
        source_uris = [f"gs://{bucket_name}/output.jsonl"]

        import_files_to_corpus(
            project_id=project_id,
            location=location,
            corpus_id=corpus_id,
            source_uris=source_uris,
            chunk_size=512,
            chunk_overlap=50
        )

        # 完了メッセージ
        print("\n" + "=" * 80)
        print("✅ セットアップが完了しました！")
        print("=" * 80)
        print()
        print("次のステップ:")
        print(f"1. .env ファイルに以下を追加してください:")
        print(f"   RAG_CORPUS_ID={corpus_id}")
        print()
        print(f"2. テストスクリプトを実行してください:")
        print(f"   python -m src.phase1.test_rag")
        print()

    except Exception as e:
        logger.error(f"セットアップ中にエラーが発生しました: {str(e)}", exc_info=True)
        print(f"\n❌ エラー: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

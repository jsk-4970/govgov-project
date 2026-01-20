"""e-Stat API ETL メイン処理

e-Stat APIから統計データを取得し、JSONL形式でGCSに保存します。
実行環境: Cloud Functions / Cloud Run
トリガー: Cloud Scheduler
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Optional

# src/commonをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from common.estat_client import EStatClient, EStatAPIError
from common.gcs_uploader import GCSUploader, GCSUploadError
from common.secret_manager import get_secret

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='{"severity": "%(levelname)s", "timestamp": "%(asctime)s", "message": "%(message)s", "module": "%(name)s"}',
)
logger = logging.getLogger(__name__)


class EStatETLPipeline:
    """e-Stat データ取得ETLパイプライン"""

    def __init__(
        self,
        project_id: str,
        bucket_name: str,
        estat_app_id: str,
        output_date: Optional[str] = None,
    ) -> None:
        """ETLパイプラインを初期化する

        Args:
            project_id: GCPプロジェクトID
            bucket_name: 出力先GCSバケット名
            estat_app_id: e-Stat APIアプリケーションID
            output_date: 出力日付（YYYY-MM-DD形式、省略時は今日）
        """
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.estat_app_id = estat_app_id
        self.output_date = output_date or datetime.now().strftime("%Y-%m-%d")

        # クライアント初期化
        self.estat_client = EStatClient(app_id=estat_app_id, request_interval=1.0)
        self.gcs_uploader = GCSUploader(bucket_name=bucket_name)

        logger.info(
            f"ETL Pipeline initialized (project={project_id}, bucket={bucket_name}, date={self.output_date})"
        )

    def run(
        self,
        max_stats_count: Optional[int] = None,
        search_kind: int = 1,
        **filter_params: Any,
    ) -> dict[str, Any]:
        """ETL処理を実行する

        Args:
            max_stats_count: 処理する統計表の最大数（テスト用、省略時は全件）
            search_kind: データ種別（1: 統計情報, 2: 小地域）
            **filter_params: getStatsListに渡すフィルタパラメータ
                - surveyYears: 調査年月
                - statsCode: 政府統計コード
                - searchWord: 検索キーワード

        Returns:
            実行結果サマリー
        """
        logger.info("=" * 80)
        logger.info("Starting e-Stat ETL Pipeline")
        logger.info("=" * 80)

        summary = {
            "start_time": datetime.now().isoformat(),
            "output_date": self.output_date,
            "stats_fetched": 0,
            "stats_uploaded": 0,
            "stats_failed": 0,
            "failed_stats_ids": [],
        }

        try:
            # ステップ1: 統計表IDリストを取得
            logger.info("Step 1: Fetching stats IDs list...")
            stats_ids = self.estat_client.get_all_stats_ids(
                search_kind=search_kind, **filter_params
            )
            summary["stats_fetched"] = len(stats_ids)

            if max_stats_count:
                logger.info(f"Limiting to first {max_stats_count} stats for testing")
                stats_ids = stats_ids[:max_stats_count]

            logger.info(f"Total stats to process: {len(stats_ids)}")

            # ステップ2: 各統計表データを取得してGCSに保存
            logger.info("Step 2: Fetching and uploading stats data...")

            for idx, stats_id in enumerate(stats_ids, start=1):
                logger.info(f"Processing {idx}/{len(stats_ids)}: {stats_id}")

                try:
                    # 統計データ取得
                    stats_data = self.estat_client.get_stats_data(stats_data_id=stats_id)

                    # VALUEレコード抽出
                    values = self.estat_client.extract_values_from_stats_data(stats_data)

                    if not values:
                        logger.warning(f"No data found for stats_id={stats_id}, skipping")
                        continue

                    # GCSにアップロード
                    destination_path = f"estat-data/{self.output_date}/{stats_id}.jsonl"
                    self.gcs_uploader.upload_jsonl(
                        data=values, destination_blob_name=destination_path
                    )

                    summary["stats_uploaded"] += 1
                    logger.info(
                        f"✓ Successfully processed {stats_id} ({len(values)} records)"
                    )

                except (EStatAPIError, GCSUploadError) as e:
                    logger.error(f"✗ Failed to process {stats_id}: {str(e)}")
                    summary["stats_failed"] += 1
                    summary["failed_stats_ids"].append(stats_id)
                    # エラーが発生しても次の統計表の処理を続行

            # ステップ3: サマリーをGCSに保存
            logger.info("Step 3: Saving execution summary...")
            summary["end_time"] = datetime.now().isoformat()
            summary_path = f"estat-data/{self.output_date}/_summary.json"
            self.gcs_uploader.upload_json(data=summary, destination_blob_name=summary_path)

            logger.info("=" * 80)
            logger.info("ETL Pipeline completed successfully")
            logger.info(f"Stats uploaded: {summary['stats_uploaded']}/{summary['stats_fetched']}")
            logger.info(f"Stats failed: {summary['stats_failed']}")
            logger.info("=" * 80)

            return summary

        except Exception as e:
            logger.error(f"ETL Pipeline failed with unexpected error: {str(e)}", exc_info=True)
            summary["end_time"] = datetime.now().isoformat()
            summary["error"] = str(e)
            raise

        finally:
            # クリーンアップ
            self.estat_client.close()


def main() -> None:
    """ローカル実行用メイン関数"""
    try:
        # 環境変数から設定を読み込む
        project_id = os.getenv("PROJECT_ID")
        bucket_name = os.getenv("BUCKET_NAME")

        # 環境変数から直接APIキーを取得
        estat_app_id = os.getenv("ESTAT_APP_ID")

        if not project_id:
            raise ValueError("PROJECT_ID environment variable is required")
        if not bucket_name:
            raise ValueError("BUCKET_NAME environment variable is required")
        if not estat_app_id:
            raise ValueError("ESTAT_APP_ID environment variable is required")

        logger.info(f"Starting e-Stat ETL (local mode)")
        logger.info(f"Project: {project_id}, Bucket: {bucket_name}")

        # ETLパイプライン実行
        pipeline = EStatETLPipeline(
            project_id=project_id,
            bucket_name=bucket_name,
            estat_app_id=estat_app_id,
        )

        # 環境変数でmax_stats_countを指定可能（デフォルト: すべて取得）
        max_stats_count = os.getenv("MAX_STATS_COUNT")
        if max_stats_count:
            max_stats_count = int(max_stats_count)

        summary = pipeline.run(max_stats_count=max_stats_count)

        logger.info("ETL execution completed")
        logger.info(json.dumps(summary, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Failed to run ETL pipeline: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # ローカル実行用
    main()

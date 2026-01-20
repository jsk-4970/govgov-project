"""e-Stat API データローカルダウンロードスクリプト

e-Stat APIから全統計データを取得し、ローカルディレクトリに保存します。
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# src/commonをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from common.estat_client import EStatClient, EStatAPIError

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='{"severity": "%(levelname)s", "timestamp": "%(asctime)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)


def download_all_estat_data(
    estat_app_id: str,
    output_dir: str,
    max_stats_count: int = None,
) -> dict:
    """e-Statデータを全てローカルにダウンロードする

    Args:
        estat_app_id: e-Stat APIアプリケーションID
        output_dir: 出力先ディレクトリ
        max_stats_count: 処理する統計表の最大数（テスト用）

    Returns:
        実行結果サマリー
    """
    logger.info("=" * 80)
    logger.info("Starting e-Stat Data Download (Local)")
    logger.info("=" * 80)

    # 出力ディレクトリ作成
    output_date = datetime.now().strftime("%Y-%m-%d")
    date_dir = Path(output_dir) / "estat-data" / output_date
    date_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {date_dir}")

    summary = {
        "start_time": datetime.now().isoformat(),
        "output_date": output_date,
        "output_dir": str(date_dir),
        "stats_fetched": 0,
        "stats_downloaded": 0,
        "stats_skipped": 0,
        "stats_failed": 0,
        "failed_stats_ids": [],
    }

    estat_client = EStatClient(app_id=estat_app_id, request_interval=1.0)

    try:
        # ステップ1: 統計表IDリストを取得
        logger.info("Step 1: Fetching all stats IDs...")
        stats_ids = estat_client.get_all_stats_ids()
        summary["stats_fetched"] = len(stats_ids)

        if max_stats_count:
            logger.info(f"Limiting to first {max_stats_count} stats for testing")
            stats_ids = stats_ids[:max_stats_count]

        logger.info(f"Total stats to process: {len(stats_ids)}")

        # ステップ2: 各統計表データを取得してローカルに保存
        logger.info("Step 2: Downloading stats data...")

        for idx, stats_id in enumerate(stats_ids, start=1):
            # レジューム機能: 既にダウンロード済みのファイルはスキップ
            output_file = date_dir / f"{stats_id}.jsonl"
            if output_file.exists():
                logger.info(f"Skipping {idx}/{len(stats_ids)}: {stats_id} (already downloaded)")
                summary["stats_downloaded"] += 1
                continue

            logger.info(f"Processing {idx}/{len(stats_ids)}: {stats_id}")

            try:
                # 統計データ取得
                stats_data = estat_client.get_stats_data(stats_data_id=stats_id)

                # VALUEレコード抽出
                values = estat_client.extract_values_from_stats_data(stats_data)

                if not values:
                    logger.warning(f"No data found for stats_id={stats_id}, skipping")
                    summary["stats_skipped"] += 1
                    continue

                # ローカルファイルに保存
                with open(output_file, "w", encoding="utf-8") as f:
                    for record in values:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")

                summary["stats_downloaded"] += 1
                logger.info(
                    f"✓ Downloaded {stats_id} ({len(values)} records) -> {output_file.name}"
                )

            except EStatAPIError as e:
                logger.error(f"✗ Failed to process {stats_id}: {str(e)}")
                summary["stats_failed"] += 1
                summary["failed_stats_ids"].append(stats_id)

        # ステップ3: サマリーをローカルに保存
        logger.info("Step 3: Saving execution summary...")
        summary["end_time"] = datetime.now().isoformat()
        summary_file = date_dir / "_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info("=" * 80)
        logger.info("Download completed successfully")
        logger.info(f"Stats downloaded: {summary['stats_downloaded']}/{summary['stats_fetched']}")
        logger.info(f"Stats skipped (no data): {summary['stats_skipped']}")
        logger.info(f"Stats failed: {summary['stats_failed']}")
        logger.info(f"Output directory: {date_dir}")
        logger.info("=" * 80)

        return summary

    except Exception as e:
        logger.error(f"Download failed with unexpected error: {str(e)}", exc_info=True)
        summary["end_time"] = datetime.now().isoformat()
        summary["error"] = str(e)
        raise

    finally:
        estat_client.close()


def main():
    """メイン実行関数"""
    try:
        # 環境変数から設定を読み込む
        estat_app_id = os.getenv("ESTAT_APP_ID")
        output_dir = os.getenv("OUTPUT_DIR", "/Users/aburi/Desktop/govgov/data")

        if not estat_app_id:
            raise ValueError("ESTAT_APP_ID environment variable is required")

        logger.info(f"e-Stat API ID: {estat_app_id[:10]}...")
        logger.info(f"Output directory: {output_dir}")

        # テスト実行の場合は環境変数でmax_stats_countを指定可能
        max_stats_count = os.getenv("MAX_STATS_COUNT")
        if max_stats_count:
            max_stats_count = int(max_stats_count)

        summary = download_all_estat_data(
            estat_app_id=estat_app_id,
            output_dir=output_dir,
            max_stats_count=max_stats_count,
        )

        logger.info("Download execution completed")
        logger.info(json.dumps(summary, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Failed to run download: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

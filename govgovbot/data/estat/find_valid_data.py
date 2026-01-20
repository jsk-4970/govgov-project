"""実際にデータが存在する統計IDを探す"""

import os
import random
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from common.estat_client import EStatClient

def main():
    estat_app_id = os.getenv("ESTAT_APP_ID")
    if not estat_app_id:
        print("Error: ESTAT_APP_ID is required")
        sys.exit(1)

    client = EStatClient(app_id=estat_app_id, request_interval=0.5)

    try:
        print("=" * 80)
        print("Finding stats IDs with actual data...")
        print("=" * 80)

        # 全統計IDを取得
        all_stats_ids = client.get_all_stats_ids()
        print(f"Total stats IDs: {len(all_stats_ids)}")

        # ランダムに100件サンプリング
        sample_size = min(100, len(all_stats_ids))
        sample_ids = random.sample(all_stats_ids, sample_size)

        print(f"Testing {sample_size} random samples...")
        print()

        valid_ids = []
        empty_count = 0
        error_count = 0

        for idx, stats_id in enumerate(sample_ids, 1):
            if idx % 10 == 0:
                print(f"Progress: {idx}/{sample_size}")

            try:
                stats_data = client.get_stats_data(stats_data_id=stats_id)
                statistical_data = stats_data["GET_STATS_DATA"]["STATISTICAL_DATA"]

                data_inf = statistical_data.get("DATA_INF", "")

                if isinstance(data_inf, dict) and "VALUE" in data_inf:
                    value = data_inf["VALUE"]
                    value_count = len(value) if isinstance(value, list) else 1

                    table_info = statistical_data.get("TABLE_INF", {})
                    title = table_info.get("STATISTICS_NAME", "N/A")
                    survey_date = table_info.get("SURVEY_DATE", "N/A")

                    print(f"\n✓ FOUND DATA: {stats_id}")
                    print(f"  Title: {title[:60]}...")
                    print(f"  Survey Date: {survey_date}")
                    print(f"  Value count: {value_count}")

                    valid_ids.append(stats_id)

                    if len(valid_ids) >= 10:
                        print(f"\nFound {len(valid_ids)} valid IDs. Stopping search.")
                        break
                else:
                    empty_count += 1

            except Exception as e:
                error_count += 1
                print(f"  Error on {stats_id}: {str(e)[:50]}")

        print("\n" + "=" * 80)
        print("Search Summary:")
        print(f"  Tested: {idx}/{sample_size}")
        print(f"  Valid (has data): {len(valid_ids)}")
        print(f"  Empty: {empty_count}")
        print(f"  Errors: {error_count}")
        print("=" * 80)

        if valid_ids:
            print("\nValid Stats IDs with data:")
            for vid in valid_ids:
                print(f"  - {vid}")
        else:
            print("\n⚠ No valid stats IDs found with actual data!")

    finally:
        client.close()

if __name__ == "__main__":
    main()

"""複数の統計IDでデータ取得をテスト"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from common.estat_client import EStatClient

def main():
    estat_app_id = os.getenv("ESTAT_APP_ID")
    if not estat_app_id:
        print("Error: ESTAT_APP_ID is required")
        sys.exit(1)

    client = EStatClient(app_id=estat_app_id, request_interval=1.0)

    try:
        # 統計表IDリストを取得
        stats_ids = client.get_all_stats_ids()
        print(f"Total stats IDs: {len(stats_ids)}")

        # 最初の10件をテスト
        print("\n" + "=" * 80)
        print("Testing first 10 stats IDs...")
        print("=" * 80)

        success_count = 0
        empty_count = 0

        for idx, stats_id in enumerate(stats_ids[:10], 1):
            print(f"\n[{idx}/10] Testing: {stats_id}")

            try:
                stats_data = client.get_stats_data(stats_data_id=stats_id)
                statistical_data = stats_data["GET_STATS_DATA"]["STATISTICAL_DATA"]

                # TOTAL_NUMBERを確認
                total_num = statistical_data.get("RESULT_INF", {}).get("TOTAL_NUMBER", 0)
                print(f"  TOTAL_NUMBER: {total_num}")

                # DATA_INFを確認
                data_inf = statistical_data.get("DATA_INF", "")

                if isinstance(data_inf, str):
                    print(f"  DATA_INF: Empty string")
                    empty_count += 1
                elif isinstance(data_inf, dict):
                    has_value = "VALUE" in data_inf
                    print(f"  DATA_INF: dict, has VALUE: {has_value}")
                    if has_value:
                        value = data_inf["VALUE"]
                        if isinstance(value, list):
                            print(f"  VALUE count: {len(value)}")
                            success_count += 1
                        elif isinstance(value, dict):
                            print(f"  VALUE: single dict")
                            success_count += 1
                else:
                    print(f"  DATA_INF: {type(data_inf)}")

            except Exception as e:
                print(f"  Error: {str(e)}")

        print("\n" + "=" * 80)
        print(f"Summary:")
        print(f"  Success (has data): {success_count}/10")
        print(f"  Empty (no data): {empty_count}/10")
        print("=" * 80)

    finally:
        client.close()

if __name__ == "__main__":
    main()

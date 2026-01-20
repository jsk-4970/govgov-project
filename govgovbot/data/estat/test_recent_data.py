"""最近のデータでテスト"""

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
        # 最近のデータを取得（2023年以降）
        print("=" * 80)
        print("Fetching recent stats (2023+)...")
        print("=" * 80)

        stats_ids = client.get_all_stats_ids(
            search_kind=1,
            surveyYears="202301-202512"  # 2023年1月から2025年12月
        )
        print(f"Total recent stats IDs: {len(stats_ids)}")
        print(f"First 5 IDs: {stats_ids[:5]}")

        # 最初の5件をテスト
        print("\n" + "=" * 80)
        print("Testing first 5 recent stats IDs...")
        print("=" * 80)

        success_count = 0
        empty_count = 0

        for idx, stats_id in enumerate(stats_ids[:5], 1):
            print(f"\n[{idx}/5] Testing: {stats_id}")

            try:
                stats_data = client.get_stats_data(stats_data_id=stats_id)
                statistical_data = stats_data["GET_STATS_DATA"]["STATISTICAL_DATA"]

                # TABLE_INFから調査日を確認
                table_inf = statistical_data.get("TABLE_INF", {})
                survey_date = table_inf.get("SURVEY_DATE", "N/A")
                title = table_inf.get("STATISTICS_NAME", "N/A")
                print(f"  Title: {title[:60]}...")
                print(f"  Survey Date: {survey_date}")

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
                            print(f"  ✓ SUCCESS - Has data!")
                            success_count += 1
                        elif isinstance(value, dict):
                            print(f"  VALUE: single dict")
                            print(f"  ✓ SUCCESS - Has data!")
                            success_count += 1
                else:
                    print(f"  DATA_INF: {type(data_inf)}")

            except Exception as e:
                print(f"  Error: {str(e)}")

        print("\n" + "=" * 80)
        print(f"Summary:")
        print(f"  Success (has data): {success_count}/5")
        print(f"  Empty (no data): {empty_count}/5")
        print("=" * 80)

    finally:
        client.close()

if __name__ == "__main__":
    main()

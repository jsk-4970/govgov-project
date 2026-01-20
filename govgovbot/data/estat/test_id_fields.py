"""getStatsListのレスポンスでIDフィールドを確認"""

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
        print("=" * 80)
        print("Fetching stats list and checking ID fields...")
        print("=" * 80)

        response = client.get_stats_list(start_position=1, limit=5)

        # TABLE_INFを取得
        stats_list_data = response["GET_STATS_LIST"].get("DATALIST_INF")
        table_inf = stats_list_data.get("TABLE_INF", [])

        if isinstance(table_inf, dict):
            table_inf = [table_inf]

        print(f"\nFound {len(table_inf)} tables")
        print("\nChecking available ID fields in first 3 tables:\n")

        for idx, table in enumerate(table_inf[:3], 1):
            print(f"[Table {idx}]")
            print(f"  Keys: {list(table.keys())}")
            print(f"  @id: {table.get('@id')}")
            print(f"  @statsDataId: {table.get('@statsDataId')}")
            print(f"  STAT_NAME: {table.get('STAT_NAME', {}).get('$', 'N/A')}")
            print(f"  TITLE: {table.get('TITLE', 'N/A')}")

            # すべての@で始まるキーを表示
            attr_keys = [k for k in table.keys() if k.startswith('@')]
            print(f"  All @ attributes: {attr_keys}")
            print()

        # 実際に1つのstatsDataIdでデータ取得を試みる
        if table_inf:
            first_table = table_inf[0]
            test_id = first_table.get('@id')

            print("=" * 80)
            print(f"Testing data retrieval with @id: {test_id}")
            print("=" * 80)

            try:
                stats_data = client.get_stats_data(stats_data_id=test_id)
                statistical_data = stats_data["GET_STATS_DATA"]["STATISTICAL_DATA"]

                total_num = statistical_data.get("RESULT_INF", {}).get("TOTAL_NUMBER", 0)
                data_inf = statistical_data.get("DATA_INF", "")

                print(f"TOTAL_NUMBER: {total_num}")
                print(f"DATA_INF is empty: {isinstance(data_inf, str)}")

                if isinstance(data_inf, dict) and "VALUE" in data_inf:
                    print(f"✓ SUCCESS - Has data!")
                else:
                    print(f"✗ NO DATA")

            except Exception as e:
                print(f"Error: {str(e)}")

    finally:
        client.close()

if __name__ == "__main__":
    main()

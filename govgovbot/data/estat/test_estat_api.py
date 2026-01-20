"""e-Stat API テストスクリプト

実際のAPIレスポンスを確認するためのデバッグスクリプト
"""

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
        # ステップ1: 統計表IDリストを取得
        print("=" * 80)
        print("Step 1: Fetching stats IDs list...")
        print("=" * 80)
        stats_ids = client.get_all_stats_ids()
        print(f"Total stats IDs fetched: {len(stats_ids)}")
        print(f"First 10 IDs: {stats_ids[:10]}")

        # ステップ2: 最初の統計表のデータを取得してレスポンスを確認
        print("\n" + "=" * 80)
        print("Step 2: Testing first stats ID...")
        print("=" * 80)
        test_id = stats_ids[0]
        print(f"Testing stats_id: {test_id}")

        stats_data = client.get_stats_data(stats_data_id=test_id)

        print("\n" + "-" * 80)
        print("Full API Response:")
        print("-" * 80)
        print(json.dumps(stats_data, indent=2, ensure_ascii=False))

        # DATA_INFを確認
        print("\n" + "-" * 80)
        print("DATA_INF check:")
        print("-" * 80)
        statistical_data = stats_data["GET_STATS_DATA"]["STATISTICAL_DATA"]

        if "DATA_INF" in statistical_data:
            data_inf = statistical_data["DATA_INF"]
            print(f"DATA_INF type: {type(data_inf)}")
            print(f"DATA_INF value: {data_inf}")

            if isinstance(data_inf, dict):
                print(f"DATA_INF keys: {data_inf.keys()}")
                if "VALUE" in data_inf:
                    print(f"VALUE exists: {type(data_inf['VALUE'])}")
        else:
            print("No DATA_INF found in response")

    finally:
        client.close()

if __name__ == "__main__":
    main()

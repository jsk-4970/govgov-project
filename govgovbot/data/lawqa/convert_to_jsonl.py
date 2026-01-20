#!/usr/bin/env python3
"""
lawqa_jp データをJSON形式からJSONL形式に変換するスクリプト
"""
import json
from pathlib import Path
from typing import Any


def convert_json_to_jsonl(
    input_file: Path, output_file: Path, flatten_samples: bool = True
) -> None:
    """JSON形式のファイルをJSONL形式に変換する

    Args:
        input_file: 入力JSONファイルのパス
        output_file: 出力JSONLファイルのパス
        flatten_samples: samplesキーがある場合、その中身を展開するか
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # samplesキーがある場合は中身を取り出す
    if flatten_samples and isinstance(data, dict) and "samples" in data:
        data = data["samples"]

    # リストでない場合はリストに変換
    if not isinstance(data, list):
        data = [data]

    # JSONL形式で出力
    with open(output_file, "w", encoding="utf-8") as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False)
            f.write("\n")

    print(f"✅ {input_file.name} → {output_file.name} (件数: {len(data)})")


def main() -> None:
    """メイン処理"""
    # データディレクトリのパス
    data_dir = Path(__file__).parent / "data"
    output_dir = Path(__file__).parent / "data_jsonl"
    output_dir.mkdir(exist_ok=True)

    # 変換対象のファイルリスト
    json_files = [
        "law_list.json",
        "selection.json",
        "selection_randomized.json",
        "selection_with_reference__randomized.json",
    ]

    print("=" * 60)
    print("lawqa_jp データをJSONL形式に変換")
    print("=" * 60)

    for json_file in json_files:
        input_path = data_dir / json_file
        output_path = output_dir / json_file.replace(".json", ".jsonl")

        if not input_path.exists():
            print(f"⚠️  {json_file} が見つかりません。スキップします。")
            continue

        try:
            # selection系のファイルはsamplesキーを展開
            flatten = json_file.startswith("selection")
            convert_json_to_jsonl(input_path, output_path, flatten_samples=flatten)
        except Exception as e:
            print(f"❌ {json_file} の変換に失敗: {e}")

    print("=" * 60)
    print(f"変換完了: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

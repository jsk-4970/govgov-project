#!/usr/bin/env python3
"""
大きなJSONLファイルを10MB以下の複数ファイルに分割するスクリプト
"""
import os
from pathlib import Path


def split_jsonl_file(input_file: str, max_size_mb: float = 10.0) -> list[str]:
    """
    JSONLファイルを指定サイズ以下の複数ファイルに分割

    Args:
        input_file: 入力JSONLファイルのパス
        max_size_mb: 1ファイルあたりの最大サイズ（MB）

    Returns:
        作成されたファイルパスのリスト
    """
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {input_file}")

    # 出力ファイル名のベース
    base_name = input_path.stem
    output_dir = input_path.parent

    created_files = []
    current_file_index = 1
    current_size = 0
    current_file = None
    current_file_path = None

    try:
        with open(input_path, 'r', encoding='utf-8') as infile:
            for line in infile:
                line_size = len(line.encode('utf-8'))

                # 新しいファイルを開始する必要があるか
                if current_file is None or current_size + line_size > max_size_bytes:
                    # 既存のファイルを閉じる
                    if current_file is not None:
                        current_file.close()
                        print(f"作成完了: {current_file_path.name} ({current_size / 1024 / 1024:.2f} MB)")

                    # 新しいファイルを開く
                    current_file_path = output_dir / f"{base_name}_part{current_file_index}.jsonl"
                    current_file = open(current_file_path, 'w', encoding='utf-8')
                    created_files.append(str(current_file_path))
                    current_size = 0
                    current_file_index += 1

                # 行を書き込む
                current_file.write(line)
                current_size += line_size

        # 最後のファイルを閉じる
        if current_file is not None:
            current_file.close()
            print(f"作成完了: {current_file_path.name} ({current_size / 1024 / 1024:.2f} MB)")

    except Exception as e:
        # エラー時は開いているファイルを閉じる
        if current_file is not None:
            current_file.close()
        raise e

    return created_files


def main():
    input_file = "/Users/aburi/Desktop/govgov/data/output_converted.jsonl"

    print(f"入力ファイル: {input_file}")

    # ファイルサイズ確認
    file_size = os.path.getsize(input_file)
    print(f"ファイルサイズ: {file_size / 1024 / 1024:.2f} MB")

    if file_size <= 10 * 1024 * 1024:
        print("ファイルサイズは10MB以下です。分割の必要はありません。")
        return

    print("\n10MB以下のファイルに分割します...")
    created_files = split_jsonl_file(input_file, max_size_mb=9.5)  # 余裕を持って9.5MBで分割

    print(f"\n合計 {len(created_files)} ファイルに分割しました:")
    for file_path in created_files:
        size = os.path.getsize(file_path)
        print(f"  - {Path(file_path).name}: {size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()

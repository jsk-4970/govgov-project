#!/usr/bin/env python3
"""
CSVファイルをJSONL形式に変換するスクリプト
"""
import csv
import json
from pathlib import Path


def convert_to_int_or_none(value: str) -> int | None:
    """文字列を整数に変換、空の場合はNoneを返す"""
    if not value or value.strip() == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


def convert_to_bool(value: str) -> bool:
    """文字列をboolに変換"""
    return value.upper() == 'TRUE'


def convert_row_to_json(row: dict) -> dict:
    """CSVの行をJSONL形式のオブジェクトに変換"""
    return {
        "sheet_type": row.get("シート種別") or None,
        "fiscal_year": convert_to_int_or_none(row.get("事業年度")),
        "budget_project_id": convert_to_int_or_none(row.get("予算事業ID")),
        "project_name": row.get("事業名") or None,
        "ministry_order": convert_to_int_or_none(row.get("府省庁の建制順")),
        "policy_ministry": row.get("政策所管府省庁") or None,
        "ministry": row.get("府省庁") or None,
        "bureau": row.get("局・庁") or None,
        "department": row.get("部") or None,
        "division": row.get("課") or None,
        "office": row.get("室") or None,
        "section": row.get("班") or None,
        "subsection": row.get("係") or None,
        "purpose": row.get("事業の目的") or None,
        "current_issues": row.get("現状・課題") or None,
        "overview": row.get("事業の概要") or None,
        "overview_url": row.get("事業概要URL") or None,
        "project_category": row.get("事業区分") or None,
        "start_year": convert_to_int_or_none(row.get("事業開始年度")),
        "start_year_unknown": convert_to_bool(row.get("開始年度不明", "FALSE")),
        "end_year": convert_to_int_or_none(row.get("事業終了(予定)年度")),
        "no_end_year": convert_to_bool(row.get("終了予定なし", "FALSE")),
        "main_expense": row.get("主要経費") or None,
        "remarks": row.get("備考") or None,
        "implementation_direct": convert_to_int_or_none(row.get("実施方法ー直接実施")),
        "implementation_subsidy": convert_to_int_or_none(row.get("実施方法ー補助")),
        "implementation_burden": convert_to_int_or_none(row.get("実施方法ー負担")),
        "implementation_grant": convert_to_int_or_none(row.get("実施方法ー交付")),
        "implementation_contribution": convert_to_int_or_none(row.get("実施方法ー分担金・拠出金")),
        "implementation_other": convert_to_int_or_none(row.get("実施方法ーその他")),
        "old_project_number": row.get("旧事業番号") or None,
        "display_order": convert_to_int_or_none(row.get("整理表表示順"))
    }


def main():
    input_file = Path("/Users/aburi/Desktop/govgov/data/1-2_RS_2024_基本情報_事業概要等.csv")
    output_file = Path("/Users/aburi/Desktop/govgov/data/output_converted.jsonl")

    print(f"入力ファイル: {input_file}")
    print(f"出力ファイル: {output_file}")

    converted_count = 0

    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)

        with open(output_file, 'w', encoding='utf-8') as jsonlfile:
            for row in reader:
                json_obj = convert_row_to_json(row)
                jsonlfile.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
                converted_count += 1

    print(f"変換完了: {converted_count}行を変換しました")


if __name__ == "__main__":
    main()

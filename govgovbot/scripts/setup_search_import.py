#!/usr/bin/env python3
"""
Discovery Engine (Vertex AI Search) への再インポートユーティリティ

手順:
 1) 既存の変換済みJSONL (data/output_converted.jsonl など) をSearch用に整形
    - 必須: id, title, uri, content
 2) GCSへアップロード (gs://BUCKET_NAME/search/import.jsonl)
 3) importDocuments を実行

環境変数:
  - PROJECT_ID
  - VERTEX_AI_SEARCH_LOCATION (default: global)
  - VERTEX_AI_SEARCH_DATA_STORE_ID
  - BUCKET_NAME
"""

import os
import sys
import json
from pathlib import Path
from typing import Iterable, Dict

from dotenv import load_dotenv
from google.cloud import storage
from google.cloud import discoveryengine_v1beta as discoveryengine


def iter_source_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def make_search_jsonl(src_path: Path, out_path: Path) -> int:
    """Search用のJSONLを生成する。

    id: 行番号ベースで採番 (srcにidがあれば優先)
    title: 「府省庁 + 事業名」を優先、無ければ project_name / ministry 等から組み立て
    uri: overview_url があれば使用
    content: 主要フィールドを結合
    """
    fields_for_content = [
        "purpose",
        "current_issues",
        "overview",
        "main_expense",
        "remarks",
    ]

    count = 0
    with out_path.open("w", encoding="utf-8") as wf:
        for i, row in enumerate(iter_source_jsonl(src_path), start=1):
            rid = str(row.get("id") or i)
            title = row.get("title")
            if not title:
                ministry = row.get("ministry") or ""
                pname = row.get("project_name") or ""
                title = (ministry + " " + pname).strip() or pname or ministry or f"record-{i}"
            uri = row.get("overview_url") or row.get("uri") or ""
            parts = []
            for k in fields_for_content:
                v = row.get(k)
                if v:
                    parts.append(f"{v}")
            content = "\n".join(parts) or (row.get("overview") or row.get("purpose") or "")
            # Discovery Engine custom schema: structDataと_id/idを明示
            # Summarization/snippetの挙動に備え、複数エイリアスを入れる
            obj = {
                "_id": rid,
                "id": rid,
                "content": content,
                "structData": {
                    "title": title,
                    "uri": uri,
                    "link": uri,
                    "content": content,
                    "text": content,
                    "body": content,
                },
            }
            wf.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1
    return count


def upload_to_gcs(bucket_name: str, local_path: Path, dest_path: str, project: str | None = None) -> str:
    client = storage.Client(project=project) if project else storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(str(local_path))
    return f"gs://{bucket_name}/{dest_path}"


def import_documents(project_id: str, location: str, data_store_id: str, gcs_uri: str) -> None:
    endpoint = "discoveryengine.googleapis.com" if location == "global" else f"{location}-discoveryengine.googleapis.com"
    client = discoveryengine.DocumentServiceClient(client_options={"api_endpoint": endpoint})
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/branches/default_branch"
    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(input_uris=[gcs_uri], data_schema="custom"),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL,
    )
    op = client.import_documents(request=request)
    print("Import operation started:", op.operation.name)
    resp = op.result()  # 完了待ち
    # エラーサンプルを表示
    try:
        errs = getattr(resp, 'error_samples', [])
        if errs:
            print("Error samples (first 3):")
            for e in errs[:3]:
                print("  -", getattr(e, 'message', str(e)))
    except Exception:
        pass
    print("Import completed.")


def main() -> int:
    load_dotenv()
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("VERTEX_AI_SEARCH_LOCATION", "global")
    data_store_id = os.getenv("VERTEX_AI_SEARCH_DATA_STORE_ID")
    bucket_name = os.getenv("BUCKET_NAME")
    if not all([project_id, data_store_id, bucket_name]):
        print("Missing env PROJECT_ID/VERTEX_AI_SEARCH_DATA_STORE_ID/BUCKET_NAME", file=sys.stderr)
        return 2

    src = Path("data/output_converted.jsonl")
    if not src.exists():
        # フォールバック: output.jsonl
        alt = Path("data/output.jsonl")
        if alt.exists():
            src = alt
        else:
            print("Source JSONL not found: data/output_converted.jsonl or data/output.jsonl", file=sys.stderr)
            return 2

    out = Path("data/search_import.jsonl")
    n = make_search_jsonl(src, out)
    print(f"Built Search JSONL: {out} ({n} lines)")

    gcs_path = upload_to_gcs(bucket_name, out, "search/import.jsonl", project=project_id)
    print("Uploaded:", gcs_path)

    import_documents(project_id, location, data_store_id, gcs_path)
    print("All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())



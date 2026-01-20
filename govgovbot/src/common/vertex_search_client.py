"""Vertex AI Search クライアント

Vertex AI Search (Discovery Engine)を使用して、
行政事業レビューデータに対する検索と回答生成を実行するクライアントを提供します。

ローカル実行やCloud Run実行の双方に対応するため、
サービスアカウント認証は以下の環境変数から自動検出します（任意）。

- GOOGLE_APPLICATION_CREDENTIALS: サービスアカウントJSONのパス
- GOOGLE_APPLICATION_CREDENTIALS_JSON: サービスアカウントJSONそのもの
- GCP_SERVICE_ACCOUNT_JSON / GCP_SA_KEY_JSON: 同上（互換）
- GCP_SA_KEY_B64: base64エンコードしたサービスアカウントJSON

いずれも未設定の場合はADC（Application Default Credentials）にフォールバックします。
"""

import logging
import os
import json
import base64
from typing import Any, Optional
from google.cloud import discoveryengine_v1beta as discoveryengine
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, TooManyRequests, ServiceUnavailable
from google.oauth2 import service_account
from collections.abc import Mapping

# ロガーの設定
logger = logging.getLogger(__name__)


class VertexAISearchClient:
    """Vertex AI Search クライアント"""

    def __init__(
        self,
        project_id: str,
        location: str,
        data_store_id: str,
    ):
        """
        Args:
            project_id: GCPプロジェクトID
            location: リージョン（例: global）
            data_store_id: データストアID
        """
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id

        # ロケーションに応じたAPIエンドポイントを設定
        if location == "global":
            api_endpoint = "discoveryengine.googleapis.com"
        else:
            api_endpoint = f"{location}-discoveryengine.googleapis.com"

        # 認証情報の組み立て（任意）
        credentials = self._build_credentials_from_env()

        # クライアント初期化（適切なエンドポイントを指定）
        self.client = discoveryengine.SearchServiceClient(
            client_options={"api_endpoint": api_endpoint},
            credentials=credentials,
        )

        # サービングコンフィグのパスを構築
        self.serving_config = (
            f"projects/{project_id}/locations/{location}/"
            f"collections/default_collection/dataStores/{data_store_id}/"
            f"servingConfigs/default_config"
        )

        logger.info(
            f"VertexAISearchClient initialized: "
            f"project={project_id}, location={location}, "
            f"data_store={data_store_id}, endpoint={api_endpoint}"
        )

    @staticmethod
    def _build_credentials_from_env() -> Optional[service_account.Credentials]:
        """環境変数からサービスアカウント認証情報を構築する。

        環境変数が見つからない場合はNoneを返し、ADCに委ねます。
        """
        # パス指定がある場合はADCに任せる（クライアントへ直接渡さずともOK）
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            return None

        json_raw = (
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            or os.getenv("GCP_SERVICE_ACCOUNT_JSON")
            or os.getenv("GCP_SA_KEY_JSON")
        )
        if not json_raw:
            b64 = os.getenv("GCP_SA_KEY_B64")
            if b64:
                try:
                    json_raw = base64.b64decode(b64).decode("utf-8")
                except Exception:
                    json_raw = None

        if not json_raw:
            return None

        try:
            info = json.loads(json_raw)
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            return service_account.Credentials.from_service_account_info(
                info, scopes=scopes
            )
        except Exception:
            # 失敗時はADCにフォールバック
            return None

    @retry(
        stop=stop_after_attempt(int(os.getenv("VERTEX_AI_RETRY_ATTEMPTS", "5"))),
        wait=wait_exponential(
            multiplier=int(os.getenv("VERTEX_AI_RETRY_MULTIPLIER", "2")),
            min=int(os.getenv("VERTEX_AI_RETRY_MIN_WAIT", "4")),
            max=int(os.getenv("VERTEX_AI_RETRY_MAX_WAIT", "60"))
        ),
        retry=retry_if_exception_type((ResourceExhausted, TooManyRequests, ServiceUnavailable)),
        reraise=True
    )
    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """
        Vertex AI Search で検索を実行し、RAG回答を生成

        切り捨て型指数バックオフによるリトライを実装:
        - ResourceExhausted (429 DSQ枯渇)
        - TooManyRequests (429 レート制限)
        - ServiceUnavailable (503 一時的エラー)

        Args:
            query: 検索クエリ
            max_results: 検索結果の最大数

        Returns:
            検索結果と生成された回答を含む辞書
            {
                "summary": "生成された回答",
                "sources": ["参照元1", "参照元2", ...],
                "results": [検索結果の詳細（デバッグ用）]
            }

        Raises:
            VertexAISearchError: API呼び出しに失敗した場合
        """
        logger.info(f"Vertex AI Search query started: query='{query}'")

        try:
            # 検索リクエストの構築
            request = discoveryengine.SearchRequest(
                serving_config=self.serving_config,
                query=query,
                page_size=max_results,
                # 非構造化データ検索の設定
                content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                    # スニペット仕様
                    snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                        return_snippet=True
                    ),
                    # 回答生成を有効化
                    summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                        summary_result_count=max_results,
                        include_citations=True,
                        ignore_adversarial_query=True,
                        ignore_non_summary_seeking_query=True,
                        model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                            preamble="あなたは行政事業レビューに関する質問に答えるアシスタントです。提供された文書を基に、正確で分かりやすい回答を日本語で提供してください。"
                        ),
                    ),
                ),
            )

            # 検索の実行
            response = self.client.search(request)

            # 回答の抽出
            summary = ""
            if hasattr(response, 'summary') and response.summary:
                if hasattr(response.summary, 'summary_text'):
                    summary = response.summary.summary_text

            # 参照元・スニペットの抽出
            sources = []
            results = []
            all_snippets: list[str] = []

            for result in response.results:
                if hasattr(result, 'document'):
                    doc = result.document

                    # タイトルやURIを取得
                    title = getattr(doc.derived_struct_data, 'title', None) if hasattr(doc, 'derived_struct_data') else None
                    uri = getattr(doc.derived_struct_data, 'link', None) if hasattr(doc, 'derived_struct_data') else None

                    # structured_dataからも情報を取得（protobuf→dict へ変換して頑健にアクセス）
                    # struct_data は MapComposite のことがあるため、辞書風アクセスを優先
                    try:
                        sd_map = getattr(doc, 'struct_data', None)
                        def map_has(m: Any, k: str) -> bool:
                            try:
                                return isinstance(m, Mapping) and k in m
                            except Exception:
                                try:
                                    return hasattr(m, 'keys') and k in m.keys()
                                except Exception:
                                    return False

                        def map_get(m: Any, k: str) -> Optional[Any]:
                            try:
                                if isinstance(m, Mapping):
                                    return m.get(k)
                                if hasattr(m, '__getitem__') and map_has(m, k):
                                    return m[k]
                            except Exception:
                                return None
                            return None

                        if sd_map:
                            if not title and map_has(sd_map, 'title'):
                                title = map_get(sd_map, 'title')
                            if not uri and map_has(sd_map, 'uri'):
                                uri = map_get(sd_map, 'uri')
                            if not uri and map_has(sd_map, 'link'):
                                uri = map_get(sd_map, 'link')
                            if map_has(sd_map, 'structData'):
                                inner = map_get(sd_map, 'structData')
                                if inner:
                                    if not title and map_has(inner, 'title'):
                                        title = map_get(inner, 'title')
                                    if not uri and map_has(inner, 'uri'):
                                        uri = map_get(inner, 'uri')
                                    if not uri and map_has(inner, 'link'):
                                        uri = map_get(inner, 'link')
                    except Exception:
                        pass

                    # ソース情報を構築
                    if title or uri:
                        source_info = title if title else uri if uri else doc.name
                        sources.append(source_info)

                    # スニペット抽出（可能な限り吸い上げる）
                    try:
                        info = getattr(result, 'snippet_info', None)
                        if info:
                            # v1beta では snippets 配列を持つ
                            if hasattr(info, 'snippets') and info.snippets:
                                for s in info.snippets:
                                    text = getattr(s, 'snippet', None) or getattr(s, 'text', None)
                                    if text:
                                        all_snippets.append(text)
                            # 実装差異に備えてdocument_snippets等も確認
                            elif hasattr(info, 'document_snippets') and info.document_snippets:
                                for s in info.document_snippets:
                                    text = getattr(s, 'snippet', None) or getattr(s, 'text', None)
                                    if text:
                                        all_snippets.append(text)
                    except Exception:
                        pass

                    results.append({
                        "title": title,
                        "uri": uri,
                        "name": doc.name
                    })

            # 回答が生成されなかった、または自動文言のみの場合はスニペットで代替
            def _is_empty_or_auto(text: str) -> bool:
                if not text:
                    return True
                lower = text.lower()
                return "a summary could not be generated" in lower or "no summary" in lower

            if _is_empty_or_auto(summary):
                if all_snippets:
                    # 重複除去して先頭数件を連結
                    seen = set()
                    unique_snips = []
                    for s in all_snippets:
                        s_norm = s.strip()
                        if s_norm and s_norm not in seen:
                            seen.add(s_norm)
                            unique_snips.append(s_norm)
                        if len(unique_snips) >= max_results:
                            break
                    snippet_summary = " ".join(unique_snips)
                    # それでも空なら最終フォールバック
                    summary = snippet_summary or "申し訳ございません。該当する情報が見つかりませんでした。"
                else:
                    logger.warning("No summary/snippets generated by Vertex AI Search")
                    summary = "申し訳ございません。該当する情報が見つかりませんでした。"

            logger.info(
                f"Search completed: summary_length={len(summary)}, "
                f"sources_count={len(sources)}"
            )

            return {
                "summary": summary,
                "sources": sources,
                "results": results,
                "snippets": all_snippets,
            }

        except ResourceExhausted as e:
            # DSQ (Daily Service Quota) 枯渇エラー
            logger.error(
                f"Vertex AI Search quota exhausted (DSQ): {str(e)}",
                exc_info=True,
                extra={"error_type": "quota_exhausted", "error_code": "429"}
            )
            raise VertexAISearchError(f"QUOTA_EXHAUSTED: {str(e)}") from e

        except TooManyRequests as e:
            # レート制限エラー
            logger.error(
                f"Vertex AI Search rate limit exceeded: {str(e)}",
                exc_info=True,
                extra={"error_type": "rate_limit", "error_code": "429"}
            )
            raise VertexAISearchError(f"RATE_LIMIT: {str(e)}") from e

        except ServiceUnavailable as e:
            # サービス一時利用不可
            logger.error(
                f"Vertex AI Search service unavailable: {str(e)}",
                exc_info=True,
                extra={"error_type": "service_unavailable", "error_code": "503"}
            )
            raise VertexAISearchError(f"SERVICE_UNAVAILABLE: {str(e)}") from e

        except Exception as e:
            # その他のエラー
            logger.error(f"Vertex AI Search query failed: {str(e)}", exc_info=True)
            raise VertexAISearchError(f"Vertex AI Search query failed: {str(e)}") from e


class VertexAISearchError(Exception):
    """Vertex AI Search API呼び出しのエラー"""
    pass

"""Vertex AI RAG Engine クライアント

Vertex AI RAG Engineを使用して、
行政事業レビューデータに対するRAGベースの回答生成を実行するクライアントを提供します。
マルチリージョンフェイルオーバーによる429エラー対策を実装しています。
"""

import logging
import os
import random
import time
from typing import Any, Dict, Optional, List
import vertexai
from vertexai.generative_models import GenerativeModel, Tool
from vertexai import rag
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted, TooManyRequests, ServiceUnavailable, InternalServerError

# Code Executionツールをインポート
try:
    from vertexai.preview.generative_models import grounding
except ImportError:
    grounding = None

# ロガーの設定
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

# マルチリージョンフェイルオーバー用のリージョンリスト
# 重要: gemini-2.0-flash-expモデルが利用可能なリージョンのみを含める
# us-east1では404エラーが発生するため除外
AVAILABLE_REGIONS: List[str] = [
    # 北米リージョン（gemini-2.0-flash-expが利用可能）
    "us-central1",  # プライマリリージョン（最も安定）
    "us-west1",
    "us-west4",
    # アジアリージョン
    "asia-northeast1",
    "asia-southeast1",
    "asia-east1",
    # ヨーロッパリージョン
    "europe-west1",
    "europe-west3",
    "europe-west4",
    # 注意: us-east1は除外（404エラーが発生するため）
]


class VertexAIRAGClient:
    """Vertex AI RAG Engine クライアント"""

    def __init__(
        self,
        project_id: str,
        location: str,
        rag_corpus_resource_name: str,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        top_k: int = 5,
        enable_multi_region: bool = True,
    ):
        """
        Args:
            project_id: GCPプロジェクトID
            location: リージョン（例: global, us-central1）
            rag_corpus_resource_name: RAG Corpusのリソース名
            model_name: 使用するモデル名
            temperature: 生成の温度パラメータ
            max_output_tokens: 最大出力トークン数
            top_k: RAG検索の上位K件
            enable_multi_region: マルチリージョンフェイルオーバーを有効化
        """
        self.project_id = project_id
        self.primary_location = location  # プライマリロケーション
        self.rag_corpus_resource_name = rag_corpus_resource_name
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_k = top_k

        # マルチリージョンフェイルオーバー設定
        self.enable_multi_region = enable_multi_region
        self.available_regions = AVAILABLE_REGIONS if enable_multi_region else [location]
        self.current_region_index = 0

        # プライマリロケーションがリストにある場合は先頭に移動
        if enable_multi_region and location in self.available_regions:
            self.available_regions.remove(location)
            self.available_regions.insert(0, location)

        # 初期化は最初のリージョンで実行
        self._init_with_region(self.available_regions[0])

        logger.info(
            f"VertexAIRAGClient initialized: "
            f"project={project_id}, primary_location={self.primary_location}, "
            f"current_region={self.available_regions[self.current_region_index]}, "
            f"multi_region={'enabled' if enable_multi_region else 'disabled'}, "
            f"available_regions={len(self.available_regions)}, "
            f"rag_corpus={rag_corpus_resource_name}, model={model_name}, top_k={top_k}"
        )

    def _init_with_region(self, region: str) -> None:
        """指定されたリージョンでVertex AIを初期化する

        Args:
            region: 初期化するリージョン
        """
        # Vertex AIの初期化
        model_location = os.getenv("MODEL_LOCATION") or region
        vertexai.init(project=self.project_id, location=model_location)

        # RAGツールの設定
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(rag_corpus=self.rag_corpus_resource_name)
                    ],
                    rag_retrieval_config=rag.RagRetrievalConfig(
                        top_k=self.top_k,
                    ),
                ),
            )
        )

        tools = [rag_retrieval_tool]
        code_execution_tool = None
        if hasattr(Tool, "from_code_execution"):
            try:
                code_execution_tool = Tool.from_code_execution()
            except (AttributeError, TypeError):
                code_execution_tool = None
        if code_execution_tool is not None:
            tools.append(code_execution_tool)

        # GenerativeModelの初期化
        self.model = GenerativeModel(
            model_name=self.model_name,
            tools=tools,
        )

        logger.info(f"Vertex AI initialized with region: {region} (model_location: {model_location})")

    def _switch_to_next_region(self) -> bool:
        """次のリージョンに切り替える

        Returns:
            次のリージョンが利用可能な場合はTrue、全リージョンを試行済みの場合はFalse
        """
        if not self.enable_multi_region:
            return False

        self.current_region_index += 1

        if self.current_region_index >= len(self.available_regions):
            # 全リージョンを試行済み
            logger.warning("All regions exhausted for multi-region failover")
            return False

        next_region = self.available_regions[self.current_region_index]
        logger.info(f"Switching to next region: {next_region} (index: {self.current_region_index})")

        # リージョン切り替え時のランダム遅延（0.5-1.0秒）
        delay = random.uniform(0.5, 1.0)
        logger.debug(f"Adding random delay of {delay:.2f} seconds before switching region")
        time.sleep(delay)

        # 新しいリージョンで再初期化
        self._init_with_region(next_region)

        return True

    def _reset_to_primary_region(self) -> None:
        """プライマリリージョンに復帰する"""
        if not self.enable_multi_region or self.current_region_index == 0:
            return

        logger.info(f"Resetting to primary region: {self.available_regions[0]}")
        self.current_region_index = 0
        self._init_with_region(self.available_regions[0])

    def generate_answer(
        self,
        query: str,
    ) -> Dict[str, Any]:
        """
        Vertex AI RAG で検索を実行し、回答を生成

        2段階リトライ戦略:
        フェーズ1: マルチリージョンフェイルオーバー（429エラー時に即座に次のリージョンへ）
        フェーズ2: 全リージョン失敗時は指数バックオフリトライ

        Args:
            query: 質問文

        Returns:
            生成された回答を含む辞書
            {
                "answer": "生成された回答",
                "grounding_metadata": グラウンディングメタデータ（参照元情報）
            }

        Raises:
            VertexAIRAGError: API呼び出しに失敗した場合
        """
        logger.info(f"Vertex AI RAG query started: query='{query}'")

        # フェーズ1: マルチリージョンフェイルオーバー
        last_error = None
        regions_tried = 0

        while regions_tried < len(self.available_regions):
            regions_tried += 1
            current_region = self.available_regions[self.current_region_index]

            try:
                logger.info(f"Attempting query with region: {current_region} (attempt {regions_tried}/{len(self.available_regions)})")
                result = self._generate_answer_internal(query)

                # 成功時はプライマリリージョンに復帰
                self._reset_to_primary_region()

                return result

            except (ResourceExhausted, TooManyRequests) as e:
                logger.warning(f"429 error in region {current_region}: {str(e)}")
                last_error = e

                # 次のリージョンに切り替え
                if not self._switch_to_next_region():
                    # 全リージョンで429エラー → フェーズ2へ
                    logger.warning("All regions returned 429 error, falling back to exponential backoff retry")
                    break

            except (ServiceUnavailable, InternalServerError) as e:
                logger.warning(f"Transient error in region {current_region}: {str(e)}")
                last_error = e

                # 一時的エラーでも次のリージョンを試行
                if not self._switch_to_next_region():
                    break

            except Exception as e:
                error_str = str(e)
                # 404エラー（モデルが見つからない）の場合は次のリージョンを試す
                if "404" in error_str or "not found" in error_str.lower():
                    logger.warning(f"404 error in region {current_region} (model not found): {error_str}")
                    last_error = e
                    # 次のリージョンに切り替え
                    if not self._switch_to_next_region():
                        break
                    continue
                
                logger.error(f"Unexpected error in region {current_region}: {error_str}", exc_info=True)
                # 予期しないエラーはすぐに失敗させる
                raise VertexAIRAGError(f"Vertex AI RAG query failed: {error_str}") from e

        # フェーズ2: 全リージョンで失敗した場合は指数バックオフでリトライ
        logger.info("Starting exponential backoff retry phase")

        # プライマリリージョンにリセット
        self._reset_to_primary_region()

        try:
            return self._generate_answer_with_exponential_backoff(query)
        except Exception as e:
            logger.error("All retry attempts failed", exc_info=True)
            raise VertexAIRAGError(f"All retry attempts failed: {str(e)}") from e

    def _generate_answer_internal(self, query: str) -> Dict[str, Any]:
        """内部的に回答を生成する（リトライなし）

        Args:
            query: 質問文

        Returns:
            生成された回答を含む辞書

        Raises:
            各種例外: API呼び出しの失敗
        """
        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }

        response = self.model.generate_content(
            query,
            generation_config=generation_config,
        )

        # レスポンスからテキストを安全に取得
        answer = ""
        blocked = False
        grounding_metadata: Optional[Any] = None
        finish_reason: Optional[str] = None
        
        try:
            if hasattr(response, "text"):
                answer = response.text
        except ValueError as e:
            # response.textにアクセスできない場合（ブロックされた、フィルタリングされたなど）
            logger.warning("Cannot get response text: %s", e)
            blocked = True
        
        if getattr(response, "candidates", None):
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            grounding_metadata = getattr(candidate, "grounding_metadata", None)
            
            # finish_reasonからブロック状態を判定
            if finish_reason:
                finish_reason_str = str(finish_reason).upper()
                if finish_reason_str in ("SAFETY", "RECITATION", "BLOCKED"):
                    blocked = True

        truncated = False
        if finish_reason:
            normalized_reason = str(finish_reason).upper()
            truncated = normalized_reason not in ("STOP", "FINISH_REASON_STOP")

        if not answer and not blocked:
            logger.warning("No answer generated by Vertex AI RAG")

        logger.info(
            "RAG query completed: answer_length=%s, finish_reason=%s, truncated=%s",
            len(answer or ""),
            finish_reason or "unknown",
            truncated,
        )

        return {
            "answer": answer,
            "grounding_metadata": grounding_metadata,
            "finish_reason": finish_reason,
            "truncated": truncated,
            "blocked": blocked,
            "status": "ok" if answer else ("blocked" if blocked else "empty"),
            "generation_config": generation_config,
        }

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
    def _generate_answer_with_exponential_backoff(self, query: str) -> Dict[str, Any]:
        """指数バックオフでリトライしながら回答を生成する

        全リージョンで429エラーが発生した後のフォールバック用。
        tenacityによる指数バックオフリトライを実装。

        Args:
            query: 質問文

        Returns:
            生成された回答を含む辞書

        Raises:
            VertexAIRAGError: リトライ後も失敗した場合
        """
        try:
            return self._generate_answer_internal(query)
        except ResourceExhausted as e:
            logger.warning("Vertex AI RAG rate limit (429) in exponential backoff: %s", e)
            raise VertexAIRAGError(f"Rate limit exceeded (429): {str(e)}") from e
        except (ServiceUnavailable, InternalServerError) as e:
            logger.warning("Vertex AI RAG transient error in exponential backoff: %s", e)
            raise VertexAIRAGError(f"Transient Vertex AI error: {str(e)}") from e
        except Exception as e:
            logger.error("Vertex AI RAG query failed in exponential backoff: %s", e, exc_info=True)
            raise VertexAIRAGError(f"Vertex AI RAG query failed: {str(e)}") from e


class VertexAIRAGError(Exception):
    """Vertex AI RAG Engine API呼び出しのエラー"""
    pass

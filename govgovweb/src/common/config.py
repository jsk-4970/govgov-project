"""設定読み込みモジュール

環境変数から設定を読み込み、アプリケーション全体で利用可能にします。
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GCPConfig:
    """GCP関連の設定"""

    project_id: str
    location: str
    bucket_name: str

    @classmethod
    def from_env(cls) -> "GCPConfig":
        """環境変数から設定を読み込む

        Returns:
            GCPConfig: GCP設定オブジェクト

        Raises:
            ValueError: 必須の環境変数が設定されていない場合
        """
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION", "asia-northeast1")
        bucket_name = os.getenv("BUCKET_NAME")

        if not project_id:
            raise ValueError("PROJECT_ID environment variable is required")
        if not bucket_name:
            raise ValueError("BUCKET_NAME environment variable is required")

        return cls(
            project_id=project_id,
            location=location,
            bucket_name=bucket_name
        )


@dataclass
class VertexAISearchConfig:
    """Vertex AI Search (Discovery Engine)関連の設定"""

    data_store_id: str
    location: str
    max_results: int

    @classmethod
    def from_env(cls) -> "VertexAISearchConfig":
        """環境変数から設定を読み込む

        Returns:
            VertexAISearchConfig: Vertex AI Search設定オブジェクト

        Raises:
            ValueError: 必須の環境変数が設定されていない場合
        """
        data_store_id = os.getenv("VERTEX_AI_SEARCH_DATA_STORE_ID")
        location = os.getenv("VERTEX_AI_SEARCH_LOCATION", "global")
        max_results = int(os.getenv("VERTEX_AI_SEARCH_MAX_RESULTS", "5"))

        if not data_store_id:
            raise ValueError("VERTEX_AI_SEARCH_DATA_STORE_ID environment variable is required")

        return cls(
            data_store_id=data_store_id,
            location=location,
            max_results=max_results
        )


@dataclass
class RAGConfig:
    """Vertex AI RAG Engine関連の設定"""

    corpus_id: str
    model_name: str
    temperature: float
    max_output_tokens: int
    similarity_top_k: int

    @classmethod
    def from_env(cls) -> "RAGConfig":
        """環境変数から設定を読み込む

        Returns:
            RAGConfig: RAG設定オブジェクト

        Raises:
            ValueError: 必須の環境変数が設定されていない場合
        """
        corpus_id = os.getenv("RAG_CORPUS_ID")
        model_name = os.getenv("MODEL_NAME", "gemini-1.5-pro")
        temperature = float(os.getenv("TEMPERATURE", "0.7"))
        max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))
        similarity_top_k = int(os.getenv("SIMILARITY_TOP_K", "5"))

        if not corpus_id:
            raise ValueError("RAG_CORPUS_ID environment variable is required")

        return cls(
            corpus_id=corpus_id,
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            similarity_top_k=similarity_top_k
        )


@dataclass
class AppConfig:
    """アプリケーション全体の設定"""

    gcp: GCPConfig
    vertex_search: Optional[VertexAISearchConfig] = None
    rag: Optional[RAGConfig] = None

    @classmethod
    def from_env(cls, require_vertex_search: bool = False, require_rag: bool = False) -> "AppConfig":
        """環境変数から設定を読み込む

        Args:
            require_vertex_search: Vertex AI Search設定を必須とするか
            require_rag: RAG設定を必須とするか

        Returns:
            AppConfig: アプリケーション設定オブジェクト

        Raises:
            ValueError: 必須設定が不足している場合
        """
        gcp = GCPConfig.from_env()

        vertex_search = None
        if require_vertex_search or os.getenv("VERTEX_AI_SEARCH_DATA_STORE_ID"):
            vertex_search = VertexAISearchConfig.from_env()

        rag = None
        if require_rag or os.getenv("RAG_CORPUS_ID"):
            rag = RAGConfig.from_env()

        return cls(
            gcp=gcp,
            vertex_search=vertex_search,
            rag=rag
        )

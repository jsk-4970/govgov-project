"""Vertex AI RAG Engine クライアント

Vertex AI RAG Engineを使用して、行政事業レビューデータに対する
質問応答を実行するクライアントを提供します。
"""

from typing import Any
import logging
from google.cloud import aiplatform
from google.cloud.aiplatform import rag
from tenacity import retry, stop_after_attempt, wait_exponential

# ロガーの設定
logger = logging.getLogger(__name__)


class VertexAIRAGClient:
    """Vertex AI RAG Engine クライアント"""

    def __init__(
        self,
        project_id: str,
        location: str,
        corpus_id: str,
        model_name: str = "gemini-1.5-pro"
    ):
        """
        Args:
            project_id: GCPプロジェクトID
            location: リージョン（例: asia-northeast1）
            corpus_id: RAGコーパスID
            model_name: 使用する生成AIモデル名
        """
        aiplatform.init(project=project_id, location=location)
        self.project_id = project_id
        self.location = location
        self.corpus_id = corpus_id
        self.model_name = model_name

        logger.info(
            f"VertexAIRAGClient initialized: "
            f"project={project_id}, location={location}, "
            f"corpus={corpus_id}, model={model_name}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        temperature: float = 0.7,
        max_output_tokens: int = 1024
    ) -> dict[str, Any]:
        """
        RAG Engineで質問に回答する

        Args:
            question: ユーザーからの質問
            similarity_top_k: 検索する関連文書の数
            temperature: 生成時のランダム性（0.0-1.0）
            max_output_tokens: 最大出力トークン数

        Returns:
            回答と参照元を含む辞書
            {
                "answer": "回答文",
                "sources": ["参照元1", "参照元2", ...],
                "contexts": ["文脈1", "文脈2", ...]  # デバッグ用
            }

        Raises:
            VertexAIRAGError: API呼び出しに失敗した場合
        """
        logger.info(f"RAG query started: question='{question}'")

        try:
            # RAGリソースの構築
            rag_resource = rag.RagResource(
                rag_corpus=f"projects/{self.project_id}/locations/{self.location}/ragCorpora/{self.corpus_id}",
            )

            # RAG検索を実行
            logger.debug(f"Retrieving contexts with similarity_top_k={similarity_top_k}")
            response = rag.retrieval_query(
                rag_resources=[rag_resource],
                text=question,
                similarity_top_k=similarity_top_k,
            )

            # 検索結果から文脈を取得
            contexts = []
            sources = []

            if hasattr(response, 'contexts') and response.contexts:
                for ctx in response.contexts.contexts:
                    contexts.append(ctx.text)
                    # ソースURIがあれば追加、なければデフォルト値
                    source = getattr(ctx, 'source_uri', 'データストア内の文書')
                    sources.append(source)

            logger.info(f"Retrieved {len(contexts)} contexts")

            # 文脈が取得できなかった場合
            if not contexts:
                logger.warning("No contexts found for the query")
                return {
                    "answer": "申し訳ございません。該当する情報が見つかりませんでした。",
                    "sources": [],
                    "contexts": []
                }

            # Geminiで回答生成
            logger.debug(f"Generating answer with model={self.model_name}")
            model = aiplatform.GenerativeModel(self.model_name)

            # プロンプト構築
            prompt = self._build_prompt(question, contexts)

            generation_response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
            )

            answer = generation_response.text
            logger.info(f"Answer generated successfully (length={len(answer)})")

            return {
                "answer": answer,
                "sources": sources,
                "contexts": contexts
            }

        except Exception as e:
            logger.error(f"RAG query failed: {str(e)}", exc_info=True)
            raise VertexAIRAGError(f"RAG query failed: {str(e)}") from e

    def _build_prompt(self, question: str, contexts: list[str]) -> str:
        """
        RAG用のプロンプトを構築

        Args:
            question: ユーザーの質問
            contexts: 検索された関連文書のテキストリスト

        Returns:
            生成AI用のプロンプト
        """
        context_text = "\n\n".join([
            f"【参照文書{i+1}】\n{ctx}"
            for i, ctx in enumerate(contexts)
        ])

        prompt = f"""あなたは行政事業レビューに関する質問に答えるアシスタントです。
以下の参照文書を基に、ユーザーの質問に日本語で回答してください。

# 参照文書
{context_text}

# ユーザーの質問
{question}

# 回答のルール（必ず遵守してください）
1. **具体性を最優先**: 参照文書から「事業名」「年度」「予算額」を必ず抽出して記載してください
2. **予算の粒度を細かく**: 予算額を示す場合、可能な限り内訳（3〜5項目）を具体的に記載してください
   - 例: 単に「600億円」ではなく「人件費250億円、システム費280億円、管理費50億円」と詳細化
3. **比較で驚きを演出**: 以下のいずれかの比較を必ず含めてください
   - 前年度との比較（増減率・増減額）
   - 他の類似事業との比較
   - 国民1人あたりの金額
   - 他省庁の類似予算との比較
4. **割合を明示**: 内訳を示す場合、金額だけでなく全体に占める割合（%）も記載してください
5. **文脈を説明**: 予算の背景や目的を1〜2文で簡潔に説明してください
6. **データ出所を明示**: 「令和〇年度行政事業レビュー」など出典を明記してください
7. 参照文書に記載がない場合は「参照文書には該当情報が見つかりませんでした」と答えてください
8. 参照文書の情報を正確に伝えることを最優先してください

# 禁止事項
- 「約〇億円」だけの粗い説明で終わらせない
- 「主な支出は人件費、システム費など」のような曖昧な表現を避ける
- データに基づかない推測や一般論を書かない

回答:"""

        return prompt


class VertexAIRAGError(Exception):
    """Vertex AI RAG API呼び出しのエラー"""
    pass
"""ファクトチェックCLIツール

Vertex AI RAG Engine を使用して、行政事業レビューデータに基づいた
ファクトチェックを実行するコマンドラインツール。

使用方法:
    python fact_check_cli.py "JICAが移民を優遇してるって本当？"
"""

import argparse
import sys
import logging
import os

# gRPC DNS解決の問題を回避するため、ネイティブDNSリゾルバを使用
# 重要: vertexai.initの前に設定する必要がある
os.environ["GRPC_DNS_RESOLVER"] = "native"

import vertexai
from vertexai.generative_models import GenerativeModel, Tool
from vertexai import rag
from tenacity import retry, stop_after_attempt, wait_exponential

# ============================================================
# 設定値（ユーザーが書き換え可能）
# ============================================================
PROJECT_ID = "govgov-473916"
LOCATION = "us-central1"  # Geminiモデルが利用可能なリージョン
RAG_CORPUS_RESOURCE_NAME = "projects/govgov-473916/locations/us-east4/ragCorpora/2305843009213693952"  # RAG CorpusはUS-East4

# その他のパラメータ
MODEL_NAME = "gemini-2.0-flash-exp"  # us-central1で利用可能なモデル
TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 2048
TOP_K = 5  # RAG検索の上位K件
# ============================================================

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VertexAIRAGClient:
    """Vertex AI RAG Engine クライアント"""

    def __init__(
        self,
        project_id: str,
        location: str,
        rag_corpus_resource_name: str,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        top_k: int = 5,
    ):
        """
        Args:
            project_id: GCPプロジェクトID
            location: リージョン（例: us-east4）
            rag_corpus_resource_name: RAG Corpusのリソース名
            model_name: 使用するモデル名
            temperature: 生成の温度パラメータ
            max_output_tokens: 最大出力トークン数
            top_k: RAG検索の上位K件
        """
        self.project_id = project_id
        self.location = location
        self.rag_corpus_resource_name = rag_corpus_resource_name
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.top_k = top_k

        # Vertex AIの初期化
        vertexai.init(project=project_id, location=location)

        # RAGツールの設定
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(rag_corpus=rag_corpus_resource_name)
                    ],
                    rag_retrieval_config=rag.RagRetrievalConfig(
                        top_k=top_k,
                    ),
                ),
            )
        )

        # GenerativeModelの初期化
        self.model = GenerativeModel(
            model_name=model_name,
            tools=[rag_retrieval_tool],
        )

        logger.info(
            f"VertexAIRAGClient initialized: "
            f"project={project_id}, location={location}, "
            f"rag_corpus={rag_corpus_resource_name}, model={model_name}, top_k={top_k}"
        )

    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """# あなたの役割
あなたは、行政事業レビューのデータを基に回答する、中立・客観的なファクトチェックAI `govgov` です。

# 指示
ユーザーの質問を分析し、以下の2パターンのどちらかで回答を生成してください。
**書式、改行、口調は下記の【例】に厳密に従ってください。** Markdown記法(`**`等)は一切使わないでください。

---

### パターンA：ファクトチェック型
**条件:** ユーザーの質問が、特定の情報の真偽を問う内容の場合 (例：「〜は本当ですか？」)
**指示:** `✅` `❌` `⚠️` の判定絵文字から回答を始める。

【例】
❌ 誤りです。

【要点】
ご質問の情報について、行政事業レビューデータ上では確認できず、当該事業の要求額は8500億円でした。

【詳細】
・事業名: 感染症対策の強化に向けた基盤整備事業
・予算要求額: 8500億円

▼情報源
※ 詳細は以下のサイトで検索してご確認ください。
https://rssystem.go.jp/top

(この回答はAIによる参考情報であり、100%の正確性を保証するものではありません)

---

### パターンB：情報提供型
**条件:** ユーザーの質問が、特定の情報の提供を求める内容の場合 (例：「〜について教えてください」)
**指示:** 【要点】から回答を始める。

【例】
【要点】
デジタル庁の運営経費に関する行政事業レビューデータによると、主要な支出は人件費、情報システム関連経費、庁舎管理費などです。

【詳細】
主な内訳は以下の通りです。
・人件費: 約250億円
・情報システム関連経費: 約300億円
・庁舎管理費など: 約50億円

▼情報源
※ 詳細は以下のサイトで検索してご確認ください。
https://rssystem.go.jp/top

(この回答はAIによる参考情報であり、100%の正確性を保証するものではありません)"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_answer(
        self,
        query: str,
    ) -> str:
        """
        Vertex AI RAG で検索を実行し、回答を生成

        Args:
            query: 質問文

        Returns:
            フォーマットされた回答文字列

        Raises:
            Exception: API呼び出しに失敗した場合
        """
        logger.info(f"Vertex AI RAG query started: query='{query}'")

        try:
            # システムプロンプトとユーザーの質問を組み合わせる
            system_prompt = self._build_system_prompt()
            full_prompt = f"{system_prompt}\n\n# ユーザーの質問\n{query}"

            # コンテンツの生成
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                }
            )

            # 回答テキストの抽出
            answer = response.text if hasattr(response, 'text') and response.text else ""

            if not answer:
                logger.warning("No answer generated by Vertex AI RAG")
                answer = "申し訳ございません。該当する情報が見つかりませんでした。\n\n(この回答はAIによる参考情報であり、100%の正確性を保証するものではありません)"

            logger.info(
                f"RAG query completed: answer_length={len(answer)}"
            )

            return answer

        except Exception as e:
            logger.error(f"Vertex AI RAG query failed: {str(e)}", exc_info=True)
            raise


def fact_check(query: str) -> str:
    """
    ファクトチェックを実行し、フォーマットされた結果を返す

    Args:
        query: ファクトチェックしたい質問文

    Returns:
        フォーマットされた回答文字列
    """
    # Vertex AI RAGクライアントの初期化
    client = VertexAIRAGClient(
        project_id=PROJECT_ID,
        location=LOCATION,
        rag_corpus_resource_name=RAG_CORPUS_RESOURCE_NAME,
        model_name=MODEL_NAME,
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        top_k=TOP_K,
    )

    # 回答生成（システムプロンプトによりフォーマット済み）
    result = client.generate_answer(query=query)

    return result


def main():
    """メイン関数"""
    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(
        description="行政事業レビューデータを用いたファクトチェックCLIツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python fact_check_cli.py "JICAが移民を優遇してるって本当？"
  python fact_check_cli.py "防衛省の2023年度の主要な事業について教えてください"
        """
    )
    parser.add_argument(
        "question",
        type=str,
        help="ファクトチェックしたい質問文"
    )

    args = parser.parse_args()

    try:
        # ファクトチェック実行
        logger.info(f"Starting fact check for question: {args.question}")
        result = fact_check(args.question)

        # 結果を出力
        print()
        print("=" * 80)
        print(result)
        print("=" * 80)
        print()

        logger.info("Fact check completed successfully")

    except Exception as e:
        logger.error(f"Fact check failed: {str(e)}", exc_info=True)
        print(f"\n❌ エラーが発生しました: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

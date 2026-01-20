import os
from typing import Any, Dict

from flask import Flask, jsonify, request
from dotenv import load_dotenv

from .twitter_poster import post_tweet
from .mention_responder import run_once as run_mentions_once


def create_app() -> Flask:
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
    
    # Secret Managerから認証情報をロード（環境変数が未設定の場合）
    try:
        from src.common.secret_manager import load_secrets_to_env
        load_secrets_to_env()
    except Exception as e:
        print(f"SECRET_MANAGER_LOAD_ERROR: {e}")
    
    app = Flask(__name__)

    @app.route("/", methods=["GET"])  # Cloud Runの疎通確認用
    def root() -> Any:
        return jsonify({"ok": True, "root": True})

    @app.route("/healthz", methods=["GET", "HEAD"])  # 明示的にHEADも許可
    def health() -> Any:
        return jsonify({"ok": True, "health": "ok"})

    @app.post("/tweet")
    def tweet() -> Any:
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        text = body.get("text")
        if not text:
            return jsonify({"error": "text is required"}), 400
        try:
            data = post_tweet(text=text)
            return jsonify({"ok": True, "data": data})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.post("/tasks/reply-latest")
    def reply_latest() -> Any:
        # Cloud Scheduler 等から叩いて、最新メンションに1回分返信する
        from .twitter_listener import reply_to_latest_mention_replying, build_sample_reply
        dry = (request.args.get("dry_run", "0").lower() in ("1", "true", "yes"))
        # dry_run 時は外部APIにアクセスせず即時応答（疎通確認用）
        if dry:
            return jsonify({
                "ok": True,
                "dry_run": True,
                "text": build_sample_reply(""),
                "note": "no external calls in dry_run"
            }), 200
        result = reply_to_latest_mention_replying(dry_run=False)
        # 定期実行時、対象が無い/既返信/レート制限は正常（200）として扱う
        reason = (result or {}).get("reason")
        # 重複返信防止の新しい理由コードも200扱いにする
        status = 200 if (
            result.get("ok")
            or reason in (
                "no_mentions",
                "no_replies",
                "already_replied",
                "no_new_mentions",
                "all_new_mentions_already_replied",
                "duplicate_content_skipped",
                "post_failed_fallback",
                "rate_limited",  # レート制限の場合は次回スケジュールで再試行
            )
        ) else 500
        return jsonify(result), status

    @app.post("/tasks/reply-new-mentions")
    def reply_new_mentions() -> Any:
        # 新着メンションを全件処理するバッチ。
        from .twitter_listener import reply_to_new_mentions_batch, build_sample_reply
        dry = (request.args.get("dry_run", "0").lower() in ("1", "true", "yes"))
        max_fetch = request.args.get("max", None)
        try:
            max_fetch_int = int(max_fetch) if max_fetch is not None else 100
        except Exception:
            max_fetch_int = 100
        if dry:
            return jsonify({
                "ok": True,
                "dry_run": True,
                "text": build_sample_reply(""),
                "note": "no external calls in dry_run"
            }), 200
        result = reply_to_new_mentions_batch(dry_run=False, max_fetch=max_fetch_int)
        reason = (result or {}).get("reason")
        status = 200 if (
            result.get("ok")
            or reason in (
                "no_mentions",
                "no_new_mentions",
                "batch_preview",
                "batch_done",
                "batch_empty",
                "rate_limited",  # レート制限の場合は次回スケジュールで再試行
            )
        ) else 500
        return jsonify(result), status

    @app.post("/tasks/mentions-run-once")
    def task_mentions_run_once() -> Any:
        """メンション差分を1回処理する（idempotent）。

        Query:
          - dry_run: 1/true で投稿せずにシミュレーション
        """
        dry = (request.args.get("dry_run", "0").lower() in ("1", "true", "yes"))
        try:
            result = run_mentions_once(dry_run=dry)
            # エラーでなければ 200 扱い。既返信のみでもOK。
            return jsonify(result), 200 if result.get("ok", False) else 500
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.get("/debug/thread")
    def debug_thread() -> Any:
        """スレッド取得のデバッグ用。

        Query:
          - id: ベースとなるツイートID（必須）
          - limit: 取得数（任意、最大100）
        """
        from .twitter_listener import fetch_conversation_tweets, fetch_conversation_latest, fetch_conversation_text
        tid = (request.args.get("id") or "").strip()
        if not tid:
            return jsonify({"ok": False, "error": "id is required"}), 400
        try:
            limit_s = request.args.get("limit")
            limit = int(limit_s) if limit_s is not None else 100
        except Exception:
            limit = 100
        tweets = fetch_conversation_tweets(tid, max_results=limit)
        latest = fetch_conversation_latest(tid)
        text = fetch_conversation_text(tid)
        return jsonify({
            "ok": True,
            "base_id": tid,
            "latest": latest,
            "tweets_count": len(tweets or []),
            "tweets": tweets,
            "concat_text_preview": (text or "")[:500]
        })
    @app.post("/api/ask")
    def api_ask() -> Any:
        """Web UIからの質問に回答するAPIエンドポイント

        Request JSON:
            {
                "question": "質問内容"
            }

        Response JSON:
            {
                "ok": true,
                "answer": "回答テキスト",
                "sources": ["URL1", "URL2", ...]
            }
        """
        from .twitter_listener import build_rag_reply

        body: Dict[str, Any] = request.get_json(silent=True) or {}
        question = body.get("question", "").strip()

        if not question:
            return jsonify({"ok": False, "error": "question is required"}), 400

        try:
            # RAGを使って回答を生成（Twitter用のフォーマット関数を使用）
            result = build_rag_reply(question, return_metadata=True)
            answer_text = result.get("answer") if isinstance(result, dict) else str(result or "")
            status = result.get("status") if isinstance(result, dict) else ("ok" if answer_text else "empty")
            raw_answer = result.get("raw_answer") if isinstance(result, dict) else answer_text
            finish_reason = result.get("finish_reason") if isinstance(result, dict) else None
            truncated = bool(result.get("truncated")) if isinstance(result, dict) else False
            blocked = bool(result.get("blocked")) if isinstance(result, dict) else False
            fallback_used = bool(result.get("fallback_used")) if isinstance(result, dict) else False
            error_message = result.get("error") if isinstance(result, dict) else None
            generation_config = result.get("generation_config") if isinstance(result, dict) else None

            # ソースURLを抽出（回答テキストからURLを分離）
            import re
            url_pattern = re.compile(r"https?://[^\s]+")
            urls = url_pattern.findall(answer_text)

            # 回答テキストからURLを除去（オプション：UIで別表示する場合）
            # answer_without_urls = url_pattern.sub("", answer).strip()

            # truncatedステータスも成功とみなす（回答は有効だが最大トークン数に達した）
            ok = status in ("ok", "truncated")

            return jsonify({
                "ok": ok,
                "status": status,
                "answer": answer_text,
                "raw_answer": raw_answer,
                "sources": urls,
                "finish_reason": finish_reason,
                "truncated": truncated,
                "blocked": blocked,
                "fallback_used": fallback_used,
                "error": error_message,
                "generation_config": generation_config,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                "ok": False,
                "error": str(e)
            }), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)



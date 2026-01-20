import logging
import os
import re
import time
from typing import Iterable, Optional, Dict, Any, List

from dotenv import load_dotenv
from google.cloud import storage
from google.cloud import firestore
import tweepy
import requests
# Vertex AI Searchは使用しません（RAG Engineのみ使用）
# from src.common.vertex_search_client import VertexAISearchClient
from src.common.vertex_rag_client import (
    VertexAIRAGClient as VertexAIRAGClientNew,
    VertexAIRAGError,
)
from src.common.factcheck_prompt import build_factcheck_instruction

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


def _load_env() -> None:
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
    # Secret Managerから認証情報をロード（環境変数が未設定の場合）
    try:
        from src.common.secret_manager import load_secrets_to_env
        load_secrets_to_env()
    except Exception as e:
        logger.warning(f"Failed to load secrets from Secret Manager: {e}")


def _max_tweet_len() -> int:
    """Tweetの最大文字数（Premiumは拡張可能）。既定は10000。

    環境変数 `X_MAX_TWEET_LEN` で上書き可能。
    """
    try:
        return int(os.getenv("X_MAX_TWEET_LEN", "10000"))
    except Exception:
        return 10000


def _get_interval(env_key: str, default_sec: int) -> int:
    try:
        return max(5, int(os.getenv(env_key, str(default_sec))))
    except Exception:
        return default_sec


def _create_client() -> tweepy.Client:
    _load_env()
    required = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        logger.error("Missing required X API credentials: %s", ",".join(missing))
        raise RuntimeError("Missing env: " + ",".join(missing))
    # デバッグ用: 認証情報が読み込まれたか確認（値の一部のみ表示）
    api_key = os.getenv("X_API_KEY", "")
    access_token = os.getenv("X_ACCESS_TOKEN", "")
    logger.info("X_API_KEY loaded: %s", "***" + api_key[-4:] if len(api_key) > 4 else "NOT SET")
    logger.info("X_ACCESS_TOKEN loaded: %s", "***" + access_token[-4:] if len(access_token) > 4 else "NOT SET")
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )


def _create_api_v1() -> tweepy.API:
    """Create Tweepy v1.1 API client for fallback endpoints."""
    _load_env()
    required = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError("Missing env: " + ",".join(missing))
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )
    return tweepy.API(auth, wait_on_rate_limit=True)


def _get_bearer_client() -> Optional[tweepy.Client]:
    """Return app-only Tweepy client if X_BEARER_TOKEN is set."""
    _load_env()
    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        return None
    try:
        return tweepy.Client(bearer_token=bearer)
    except Exception:
        return None


def _get_firestore_client() -> Optional[firestore.Client]:
    """Return Firestore client for state persistence.

    Uses FIRESTORE_COLLECTION environment variable (default: 'mentions').
    """
    try:
        project_id = os.getenv("PROJECT_ID")
        if project_id:
            return firestore.Client(project=project_id)
        return firestore.Client()
    except Exception as e:
        logger.warning(f"Failed to create Firestore client: {e}")
        return None


def _get_mentions_collection() -> Optional[firestore.CollectionReference]:
    """Return Firestore collection reference for mentions."""
    client = _get_firestore_client()
    if not client:
        return None
    collection_name = os.getenv("FIRESTORE_COLLECTION", "mentions")
    return client.collection(collection_name)


def _get_state_bucket() -> Optional[storage.Bucket]:
    """Return GCS bucket for state persistence if STATE_BUCKET is set."""
    bucket_name = os.getenv("STATE_BUCKET")
    if not bucket_name:
        return None
    try:
        client = storage.Client()
        return client.bucket(bucket_name)
    except Exception:
        return None


def _read_last_id(object_name: str) -> Optional[str]:
    bucket = _get_state_bucket()
    if not bucket:
        return None
    try:
        blob = bucket.blob(object_name)
        if not blob.exists():
            return None
        data = blob.download_as_text().strip()
        return data or None
    except Exception:
        return None


def _write_last_id(object_name: str, value: str) -> None:
    bucket = _get_state_bucket()
    if not bucket:
        return
    try:
        blob = bucket.blob(object_name)
        blob.upload_from_string(str(value), content_type="text/plain")
    except Exception:
        pass


def _is_newer_id(current_id: Optional[str], last_id: Optional[str]) -> bool:
    if not current_id:
        return False
    if not last_id:
        return True
    try:
        return int(current_id) > int(last_id)
    except Exception:
        return str(current_id) > str(last_id)


def _is_auto_summary(text: Optional[str]) -> bool:
    """Return True if Vertex Search returned a generic 'no summary' message."""
    if not text:
        return True
    t = str(text).strip()
    lower = t.lower()
    # English canned messages
    if (
        "a summary could not be generated" in lower
        or "no summary" in lower
        or "here are the results" in lower
    ):
        return True
    # Japanese canned messages
    if (
        "検索語句の要約を生成できません" in t
        or "要約を生成できません" in t
        or "以下が検索結果" in t
    ):
        return True
    return False


def fetch_conversation_text(tweet_id: str, max_results: int = 50) -> Optional[str]:
    """Fetch the conversation thread text for a tweet id using app-only search.

    Returns a concatenated text (newest to oldest) or None if not available.
    """
    client = _get_bearer_client()
    if not client:
        return None
    try:
        tw = client.get_tweet(id=tweet_id, tweet_fields=["conversation_id","author_id","text"]).data
        conv_id = getattr(tw, "conversation_id", None)
        base_text = getattr(tw, "text", None)
        if not conv_id:
            return base_text
        resp = client.search_recent_tweets(
            query=f"conversation_id:{conv_id}",
            max_results=min(100, max(10, max_results)),
            sort_order="recency",
            tweet_fields=["author_id","created_at"],
        )
        texts: List[str] = []
        for t in (resp.data or []):
            txt = getattr(t, "text", None)
            if txt:
                texts.append(txt)
        # include base tweet text if not already
        if base_text:
            texts.append(base_text)
        if not texts:
            return None
        # newest first
        return "\n".join(texts)
    except Exception:
        return None


def _get_me_identity() -> tuple[Optional[str], Optional[str]]:
    """自アカウントの user_id と username を返す。失敗時は (None, None)。"""
    try:
        client = _create_client()
        me = client.get_me().data
        uid = None
        uname = None
        try:
            uid = str(me["id"]) if isinstance(me, dict) else str(me.id)
        except Exception:
            uid = None
        try:
            uname = me["username"] if isinstance(me, dict) else me.username
        except Exception:
            uname = None
        return uid, uname
    except Exception:
        return None, None


def fetch_conversation_latest(tweet_id: str) -> Optional[dict]:
    """会話スレッドの最新ツイート情報を返す。

    Returns
    -------
    Optional[dict]
        {"id": str, "author_id": str | None, "text": str | None}
    """
    # まずは bearer クライアントを優先（検索レートが緩い）
    client = _get_bearer_client() or _create_client()
    try:
        tw = client.get_tweet(id=tweet_id, tweet_fields=["conversation_id", "author_id", "text"]).data
        conv_id = getattr(tw, "conversation_id", None)
        if not conv_id:
            # 会話IDが取れない場合は元ツイートをそのまま返す
            return {
                "id": getattr(tw, "id", None) or tweet_id,
                "author_id": getattr(tw, "author_id", None),
                "text": getattr(tw, "text", None),
            }
        resp = client.search_recent_tweets(
            query=f"conversation_id:{conv_id}",
            max_results=min(100, max(10, 50)),
            sort_order="recency",
            tweet_fields=["author_id", "created_at", "text"],
        )
        data = resp.data or []
        # recency ソートなので先頭を最新とみなす
        if data:
            t = data[0]
            return {
                "id": getattr(t, "id", None),
                "author_id": getattr(t, "author_id", None),
                "text": getattr(t, "text", None),
            }
        # 取得できなかった場合は元ツイート
        return {
            "id": getattr(tw, "id", None) or tweet_id,
            "author_id": getattr(tw, "author_id", None),
            "text": getattr(tw, "text", None),
        }
    except Exception:
        return None


def fetch_conversation_tweets(tweet_id: str, max_results: int = 100) -> Optional[List[dict]]:
    """会話スレッドのツイート一覧（新しい順）を返す。

    Returns
    -------
    Optional[List[dict]]
        [{"id": str, "author_id": str | None, "text": str | None}]

    備考: recent 検索のため最大100件・直近7日程度が対象。
    """
    client = _get_bearer_client() or _create_client()
    try:
        tw = client.get_tweet(id=tweet_id, tweet_fields=["conversation_id", "author_id", "text"]).data
        conv_id = getattr(tw, "conversation_id", None) or tweet_id
        resp = client.search_recent_tweets(
            query=f"conversation_id:{conv_id}",
            max_results=min(100, max(10, max_results)),
            sort_order="recency",
            tweet_fields=["author_id", "created_at", "text"],
        )
        results: List[dict] = []
        for t in (resp.data or []):
            results.append({
                "id": getattr(t, "id", None),
                "author_id": getattr(t, "author_id", None),
                "text": getattr(t, "text", None),
            })
        # ベースツイートも含めたい場合は末尾に追加（重複チェック）
        base_id = getattr(tw, "id", None)
        base_author = getattr(tw, "author_id", None)
        base_text = getattr(tw, "text", None)
        if base_id and all(str(it.get("id")) != str(base_id) for it in results):
            results.append({"id": base_id, "author_id": base_author, "text": base_text})
        return results
    except Exception:
        return None


def _is_replied_in_firestore(tweet_id: str) -> bool:
    """Firestoreで返信済みフラグをチェックする。

    Returns
    -------
    bool
        True if the tweet is marked as replied in Firestore.
    """
    collection = _get_mentions_collection()
    if not collection:
        logger.debug(f"Firestore collection not available, skipping check for tweet {tweet_id}")
        return False
    try:
        doc_ref = collection.document(str(tweet_id))
        doc = doc_ref.get()
        if not doc.exists:
            return False
        data = doc.to_dict()
        replied = bool(data.get("replied", False))
        if replied:
            logger.info(f"Tweet {tweet_id} is already marked as replied in Firestore")
        return replied
    except Exception as e:
        logger.warning(f"Failed to check replied status in Firestore for tweet {tweet_id}: {e}")
        return False


def _mark_replied_in_firestore(tweet_id: str, reply_tweet_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Firestoreで返信済みフラグを立てる。

    Parameters
    ----------
    tweet_id: str
        元のツイートID
    reply_tweet_id: Optional[str]
        返信ツイートID（オプション）
    metadata: Optional[Dict[str, Any]]
        追加メタデータ（オプション）
    """
    collection = _get_mentions_collection()
    if not collection:
        logger.warning(f"Firestore collection not available, cannot mark tweet {tweet_id} as replied")
        return
    try:
        doc_ref = collection.document(str(tweet_id))
        data = {
            "replied": True,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        if reply_tweet_id:
            data["reply_tweet_id"] = str(reply_tweet_id)
        if metadata:
            data.update(metadata)
        # デバッグ用: 保存するデータをログに出力
        logger.debug(f"Saving to Firestore for tweet {tweet_id}: reply_tweet_id={reply_tweet_id}, metadata={metadata}, data={data}")
        doc_ref.set(data, merge=True)
        reply_id_log = f" (reply_id: {reply_tweet_id})" if reply_tweet_id else ""
        mode_log = f" (mode: {metadata.get('mode')})" if metadata and metadata.get('mode') else ""
        logger.info(f"Marked tweet {tweet_id} as replied in Firestore{reply_id_log}{mode_log}")
    except Exception as e:
        logger.error(f"Failed to mark replied in Firestore for tweet {tweet_id}: {e}", exc_info=True)


def _already_replied_to(target_tweet_id: str) -> bool:
    """Return True if our account has already replied to the target tweet.

    Strategy
    --------
    1) Check Firestore first (fastest)
    2) If not in Firestore, check Twitter API
    3) Resolve the conversation_id of the target tweet
    4) Search recent tweets in the conversation from our account
    5) If any of them has referenced_tweets with type 'replied_to' and id==target, treat as already replied
    """
    # First check Firestore
    if _is_replied_in_firestore(target_tweet_id):
        return True

    # Fallback to Twitter API check (重要: Firestoreが使えない場合でもこのチェックは実行される)
    try:
        client = _create_client()
        # who am I
        me = client.get_me().data
        me_username = None
        try:
            me_username = me["username"] if isinstance(me, dict) else me.username
        except Exception:
            pass

        # step1: get conversation id
        tw = client.get_tweet(id=target_tweet_id, tweet_fields=["conversation_id"]).data
        conv_id = None
        try:
            conv_id = tw["conversation_id"] if isinstance(tw, dict) else getattr(tw, "conversation_id", None)
        except Exception:
            conv_id = None
        conv_id = conv_id or target_tweet_id

        # step2: search my tweets in this conversation
        if not me_username:
            logger.warning(f"Cannot determine bot username, skipping Twitter API check for tweet {target_tweet_id}")
            return False
        q = f"conversation_id:{conv_id} from:{me_username}"
        resp = client.search_recent_tweets(
            query=q,
            max_results=50,
            sort_order="recency",
            tweet_fields=["referenced_tweets"],
        )
        for t in (resp.data or []):
            refs = getattr(t, "referenced_tweets", None) or []
            try:
                reply_tweet_id = str(getattr(t, "id", None)) if getattr(t, "id", None) is not None else None
                for ref in refs:
                    rtype = getattr(ref, "type", None)
                    rid = getattr(ref, "id", None)
                    if rtype == "replied_to" and str(rid) == str(target_tweet_id):
                        # Mark as replied in Firestore for future checks (if Firestore is available)
                        logger.info(f"Found existing reply to tweet {target_tweet_id} via Twitter API (reply_id: {reply_tweet_id})")
                        _mark_replied_in_firestore(target_tweet_id, reply_tweet_id=reply_tweet_id)
                        return True
            except Exception:
                continue
        return False
    except Exception as e:
        logger.warning(f"Twitter API check for already replied failed for tweet {target_tweet_id}: {e}")
        # 失敗時は安全側（未返信とみなす）だが、ログに記録
        return False


def poll_replies_to_me(limit: int = 20) -> Iterable[dict]:
    """自社アカウント宛の直近の返信を取得（to:handle ベース）。"""
    client = _create_client()
    me = client.get_me().data
    # 画面名は環境変数があれば優先
    handle = os.getenv("X_BOT_SCREEN_NAME")
    if not handle:
        try:
            handle = me["username"] if isinstance(me, dict) else me.username
        except Exception:
            handle = None
    if not handle:
        return []

    q = f"to:{handle} -from:{handle}"
    try:
        resp = client.search_recent_tweets(
            query=q,
            max_results=min(max(10, limit), 100),
            sort_order="recency",
            expansions=["author_id"],
            user_fields=["username"],
            tweet_fields=["conversation_id"],
        )
        user_map = {}
        includes = getattr(resp, "includes", None)
        if includes and getattr(includes, "users", None):
            for u in includes["users"] if isinstance(includes, dict) else includes.users:
                uid = getattr(u, "id", None)
                uname = getattr(u, "username", None)
                if uid and uname:
                    user_map[uid] = uname
        for t in (resp.data or []):
            author_id = getattr(t, "author_id", None)
            yield {
                "id": getattr(t, "id", None),
                "text": getattr(t, "text", None),
                "author_username": user_map.get(author_id),
                "conversation_id": getattr(t, "conversation_id", None),
            }
    except Exception:
        return []


def reply_to_latest_replier(dry_run: bool = True) -> Dict[str, Any]:
    """自社ポストに反応した最新ユーザーに対し、通常投稿（非スレッド）で回答を投稿。"""
    from .twitter_poster import post_tweet

    items = list(poll_replies_to_me(limit=10))
    if not items:
        return {"ok": False, "reason": "no_replies"}
    latest = items[0]
    # すでに同ツイートへ返信済みならスキップ
    try:
        if _already_replied_to(str(latest["id"])):
            return {"ok": True, "reason": "already_replied", "target": latest}
    except Exception:
        pass

    # スレッド本文を取得してクエリ生成
    conv_text = fetch_conversation_text(str(latest["id"]))
    base_text = conv_text or latest.get("text") or ""
    reply_result = build_rag_reply(base_text, return_metadata=True)
    
    # メタデータから回答とステータスを取得
    if isinstance(reply_result, dict):
        reply_text = reply_result.get("answer", "")
        reply_status = reply_result.get("status", "ok")
    else:
        reply_text = reply_result or ""
        reply_status = "ok"
    
    # レート制限の場合は返信を送らない
    if reply_status == "rate_limited":
        logger.info("Skipping reply due to rate limit (429). Will retry on next schedule.")
        return {"ok": True, "reason": "rate_limited", "target": latest}

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "target": latest,
            "text": reply_text,
        }

    data = post_tweet(text=reply_text)
    return {"ok": True, "dry_run": False, "data": data}


def reply_to_latest_replier_replying(dry_run: bool = True) -> Dict[str, Any]:
    """自社ポストに反応した最新ユーザーのツイートに直接返信。

    失敗（403など）の場合は通常投稿にフォールバック。
    """
    from .twitter_poster import post_tweet

    items = list(poll_replies_to_me(limit=10))
    if not items:
        # Fallback: メンションから拾う
        mention_items = list(poll_mentions(limit=10))
        if not mention_items:
            return {"ok": False, "reason": "no_replies"}
        items = mention_items
    latest = items[0]

    conv_text = fetch_conversation_text(str(latest["id"]))
    base_text = conv_text or latest.get("text") or ""
    reply_result = build_rag_reply(base_text, return_metadata=True)
    
    # メタデータから回答とステータスを取得
    if isinstance(reply_result, dict):
        reply_text = reply_result.get("answer", "")
        reply_status = reply_result.get("status", "ok")
    else:
        reply_text = reply_result or ""
        reply_status = "ok"
    
    # レート制限の場合は返信を送らない
    if reply_status == "rate_limited":
        logger.info("Skipping reply due to rate limit (429). Will retry on next schedule.")
        return {"ok": True, "reason": "rate_limited", "target": latest}

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "target": latest,
            "text": reply_text,
        }

    # まずは直接返信を試みる
    try:
        data = post_tweet(text=reply_text, in_reply_to_tweet_id=str(latest["id"]))
        return {"ok": True, "dry_run": False, "data": data, "mode": "reply"}
    except Exception as e:
        print("POST_DIRECT_REPLY_ERROR:" + str(e))
        # 通常投稿にフォールバック
        data = post_tweet(text=reply_text)
        return {"ok": True, "dry_run": False, "data": data, "mode": "post"}


def reply_to_latest_mention_replying(dry_run: bool = True) -> Dict[str, Any]:
    """最新のメンションに対して直接返信（失敗時は通常投稿にフォールバック）。

    Firestoreで返信済みフラグをチェックし、未返信のもののみを処理します。
    """
    from .twitter_poster import post_tweet

    # ポーリングでメンション一覧を取得
    items = list(poll_mentions(limit=10))
    if not items:
        return {"ok": False, "reason": "no_mentions"}

    def is_reply_open(it: dict) -> bool:
        rs = it.get("reply_settings")
        return (rs is None) or (str(rs).lower() == "everyone")

    # 返信許可のある候補から順に未返信のものを選ぶ
    candidates = [it for it in items if is_reply_open(it)] or items
    target = None
    for it in candidates:
        tid = str(it.get("id")) if it.get("id") is not None else None
        if not tid:
            continue
        
        # Firestoreで返信済みチェック
        if _is_replied_in_firestore(tid):
            continue
        
        # 追加チェック: _already_replied_to でも確認
        try:
            if _already_replied_to(tid):
                continue
        except Exception:
            # 判定失敗時は未返信とみなして処理する
            pass
        
        target = it
        break
    
    if target is None:
        # すべて既に返信済み
        return {"ok": True, "reason": "all_already_replied"}

    # スレッド全体の内容を取得してRAG Engineに渡す
    tid = str(target.get("id"))
    conv_text = fetch_conversation_text(tid)
    base_text = conv_text or target.get("text") or ""
    
    # RAG Engineで回答生成（メタデータも取得）
    reply_result = build_rag_reply(base_text, return_metadata=True)
    
    # メタデータから回答とステータスを取得
    if isinstance(reply_result, dict):
        reply_text = reply_result.get("answer", "")
        reply_status = reply_result.get("status", "ok")
    else:
        reply_text = reply_result or ""
        reply_status = "ok"
    
    # レート制限の場合は返信を送らない（別のリージョンで成功した場合のみ返信）
    if reply_status == "rate_limited":
        logger.info("Skipping reply due to rate limit (429). Will retry on next schedule.")
        return {"ok": True, "reason": "rate_limited", "target": target}

    author_username = target.get("author_username")

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "target": target,
            "text": reply_text,
        }

    # マルチリージョンでの重複返信を防ぐため、返信直前に再度Firestoreでチェック
    if _is_replied_in_firestore(tid):
        logger.info(f"Tweet {tid} is already replied (checked before posting), skipping")
        return {"ok": True, "reason": "already_replied_before_post", "target": target}
    
    # まず返信
    try:
        data = post_tweet(text=reply_text, in_reply_to_tweet_id=str(target["id"]))
        reply_tweet_id = data.get("id") if isinstance(data, dict) else getattr(data, "id", None)
        logger.info(f"Post reply successful for tweet {tid}: reply_tweet_id={reply_tweet_id}, data={data}")
        # 成功したらFirestoreにフラグを立てる（429以外で返信成功したら記録）
        _mark_replied_in_firestore(tid, reply_tweet_id=reply_tweet_id, metadata={"mode": "reply"})
        return {"ok": True, "dry_run": False, "data": data, "mode": "reply"}
    except Exception as e:
        print("POST_MENTION_REPLY_ERROR:" + str(e))
        # 重複投稿（duplicate content）の場合はフォールバックを試さずスキップしてFirestoreに記録
        try:
            err = str(e).lower()
        except Exception:
            err = ""
        if "duplicate content" in err:
            _mark_replied_in_firestore(tid, metadata={"reason": "duplicate_content"})
            return {"ok": True, "reason": "duplicate_content_skipped", "target": target}

        # フォールバック前にも再度チェック（マルチリージョン対策）
        if _is_replied_in_firestore(tid):
            logger.info(f"Tweet {tid} is already replied (checked before fallback), skipping")
            return {"ok": True, "reason": "already_replied_before_fallback", "target": target}
        
        # 通常投稿にフォールバック（@usernameを先頭に付与）
        prefix = f"@{author_username} " if author_username else ""
        allowed = 280 - len(prefix)
        if allowed <= 1:
            final_text = prefix + reply_text[: max(0, 280 - len(prefix))]
        elif len(reply_text) > allowed:
            final_text = prefix + reply_text[: allowed - 1] + "…"
        else:
            final_text = prefix + reply_text
        try:
            data = post_tweet(text=final_text)
            reply_tweet_id = data.get("id") if isinstance(data, dict) else getattr(data, "id", None)
            # 通常投稿が成功した場合もFirestoreにフラグを立てる（429以外で返信成功したら記録）
            _mark_replied_in_firestore(tid, reply_tweet_id=reply_tweet_id, metadata={"mode": "post_fallback"})
            return {"ok": True, "dry_run": False, "data": data, "mode": "post"}
        except Exception as e2:
            # フォールバックも失敗した場合は、429エラー以外の場合のみFirestoreに記録
            err_str = str(e2).lower() if hasattr(e2, '__str__') else ""
            if "429" not in err_str and "rate limit" not in err_str:
                # 429以外のエラーは記録（再処理を防ぐ）
                _mark_replied_in_firestore(tid, metadata={"reason": "post_failed", "error": str(e2)})
            return {"ok": True, "reason": "post_failed_fallback", "error": str(e2)}


def reply_to_new_mentions_batch(dry_run: bool = True, max_fetch: int = 100) -> Dict[str, Any]:
    """新着メンションを全件処理する（スレッド全文を用いて回答し、各ツイートに直接返信）。

    仕様:
      - ポーリングでメンション一覧を取得
      - Firestoreで返信済みフラグをチェック
      - 未返信のメンションのみを処理
      - 返信許可が "everyone" または未指定のものを優先
      - 各メンションについて、会話スレッド全文を取得して回答を生成
      - 重複投稿(duplicate content)はスキップしてFirestoreに記録
      - 返信成功時にFirestoreにフラグを立てる
      - デフォルトでスロットリングは無効化して高速処理
    """
    from .twitter_poster import post_tweet

    # ポーリングでメンション一覧を取得
    items = list(poll_mentions(limit=max(10, min(max_fetch, 100))))
    if not items:
        return {"ok": True, "reason": "no_mentions", "processed": 0}

    def is_reply_open(it: dict) -> bool:
        rs = it.get("reply_settings")
        return (rs is None) or (str(rs).lower() == "everyone")

    # 返信許可のあるものを優先
    candidates = [it for it in items if is_reply_open(it)] or items

    def _as_int(x: Any) -> int:
        try:
            return int(str(x))
        except Exception:
            return 0

    # ID昇順で古いものから処理
    candidates_sorted = sorted(
        [it for it in candidates if it.get("id") is not None],
        key=lambda it: _as_int(it.get("id")),
    )

    # Firestoreで返信済みチェックをして、未返信のものだけを洗い出す
    unprocessed: List[Dict[str, Any]] = []
    for it in candidates_sorted:
        tid = str(it.get("id"))
        if not tid:
            continue
        
        # Firestoreで返信済みチェック
        if _is_replied_in_firestore(tid):
            continue
        
        # 追加チェック: Twitter APIでも返信済みか確認
        try:
            if _already_replied_to(tid):
                continue
        except Exception:
            # 判定失敗時は未返信とみなして処理する
            pass
        
        # 追加チェック: 会話の最新ツイートが自分なら返信済みとみなす
        me_id, _ = _get_me_identity()
        try:
            latest = fetch_conversation_latest(tid)
            latest_author_id = (latest or {}).get("author_id")
            if me_id and latest_author_id and str(latest_author_id) == str(me_id):
                # Firestoreに記録
                _mark_replied_in_firestore(tid, metadata={"reason": "latest_is_me"})
                continue
        except Exception:
            pass
        
        # 未返信なので処理対象に追加
        unprocessed.append(it)

    if not unprocessed:
        return {"ok": True, "reason": "all_already_replied", "processed": 0, "total_fetched": len(items)}

    processed = 0
    skipped_duplicate = 0
    fallback_posted = 0
    failed_fallback = 0
    previews: List[Dict[str, Any]] = []

    # 未返信のメンションを処理
    for it in unprocessed:
        tid = str(it.get("id"))
        author_username = it.get("author_username")

        # スレッド本文を取得して回答生成（全文、メタデータも取得）
        conv_text = fetch_conversation_text(tid)
        base_text = conv_text or it.get("text") or ""
        reply_result = build_rag_reply(base_text, return_metadata=True)
        
        # メタデータから回答とステータスを取得
        if isinstance(reply_result, dict):
            reply_text = reply_result.get("answer", "")
            reply_status = reply_result.get("status", "ok")
        else:
            reply_text = reply_result or ""
            reply_status = "ok"
        
        # レート制限の場合は返信を送らない（別のリージョンで成功した場合のみ返信）
        if reply_status == "rate_limited":
            logger.info("Skipping reply due to rate limit (429) for tweet %s. Will retry on next schedule.", tid)
            continue

        if dry_run:
            previews.append({"id": tid, "text": reply_text})
            continue

        # マルチリージョンでの重複返信を防ぐため、返信直前に再度Firestoreでチェック
        if _is_replied_in_firestore(tid):
            logger.info(f"Tweet {tid} is already replied (checked before posting), skipping")
            continue

        # 直接返信を試みる
        reply_tweet_id = None
        try:
            data = post_tweet(text=reply_text, in_reply_to_tweet_id=tid, skip_throttle=True)
            reply_tweet_id = data.get("id") if isinstance(data, dict) else getattr(data, "id", None)
            logger.info(f"Post reply successful for tweet {tid}: reply_tweet_id={reply_tweet_id}, data={data}")
            # 成功したらFirestoreにフラグを立てる（429以外で返信成功したら記録）
            _mark_replied_in_firestore(tid, reply_tweet_id=reply_tweet_id, metadata={"mode": "reply"})
            processed += 1
            continue
        except Exception as e:
            # duplicate content はスキップしてFirestoreに記録
            err = ""
            try:
                err = str(e).lower()
            except Exception:
                pass
            if "duplicate content" in err:
                _mark_replied_in_firestore(tid, metadata={"reason": "duplicate_content"})
                skipped_duplicate += 1
                continue

            # 通常投稿にフォールバック（@username 付与）
            prefix = f"@{author_username} " if author_username else ""
            allowed = 280 - len(prefix)
            if allowed <= 1:
                final_text = prefix + reply_text[: max(0, 280 - len(prefix))]
            elif len(reply_text) > allowed:
                final_text = prefix + reply_text[: allowed - 1] + "…"
            else:
                final_text = prefix + reply_text

            # フォールバック前にも再度チェック（マルチリージョン対策）
            if _is_replied_in_firestore(tid):
                logger.info(f"Tweet {tid} is already replied (checked before fallback), skipping")
                continue
            try:
                data = post_tweet(text=final_text, skip_throttle=True)
                reply_tweet_id = data.get("id") if isinstance(data, dict) else getattr(data, "id", None)
                # フォールバック成功時もFirestoreにフラグを立てる（429以外で返信成功したら記録）
                _mark_replied_in_firestore(tid, reply_tweet_id=reply_tweet_id, metadata={"mode": "post_fallback"})
                fallback_posted += 1
            except Exception as e2:
                # フォールバックも失敗した場合はFirestoreに記録しない（429エラーの場合は再試行可能にする）
                # ただし、duplicate contentなどの場合は記録する
                err_str = str(e2).lower() if hasattr(e2, '__str__') else ""
                if "duplicate content" in err_str or "403" in err_str:
                    _mark_replied_in_firestore(tid, metadata={"reason": "post_failed", "error": str(e2)})
                failed_fallback += 1

    result: Dict[str, Any] = {
        "ok": True,
        "processed": processed,
        "skipped_duplicate": skipped_duplicate,
        "fallback_posted": fallback_posted,
        "failed_fallback": failed_fallback,
        "total_fetched": len(items),
        "unprocessed_count": len(unprocessed),
    }
    if dry_run:
        result.update({"dry_run": True, "previews": previews, "reason": "batch_preview"})
    else:
        if processed == 0 and fallback_posted == 0:
            result.update({"reason": "batch_empty"})
        else:
            result.update({"reason": "batch_done"})
    return result


def poll_mentions(since_id: Optional[str] = None, limit: int = 20) -> Iterable[dict]:
    """Fetch recent mentions using polling (simple alternative to streams).

    Parameters
    ----------
    since_id: Optional[str]
        Return results with a Tweet ID greater than (that is, more recent than) the specified ID.
    limit: int
        Maximum number of mentions to fetch.
    """
    _load_env()
    
    # 重要: Bearer Tokenを使って直接APIにアクセスを試みる
    # 
    # 理由:
    # - OAuth 1.0aのget_users_mentions()は、Free/Basicプランでは401エラーになることがある
    # - Bearer Tokenを使った直接HTTPリクエストなら、低いアクセスレベルでも動作する
    # - 詳細は docs/X_API_AUTHENTICATION.md を参照
    #
    bearer_token = os.getenv("X_BEARER_TOKEN")
    if bearer_token:
        try:
            # ユーザーIDを取得
            client = _create_client()
            try:
                me_resp = client.get_me()
                me = me_resp.data if me_resp is not None else None
                if me is None:
                    raise ValueError("get_me returned empty response")
                user_id = me["id"] if isinstance(me, dict) else me.id
            except Exception as e:
                logger.warning("poll_mentions: failed to get user_id, trying with Bearer Token only: %s", e)
                # Bearer Tokenのみで試す場合、環境変数からユーザーIDを取得
                user_id = os.getenv("X_BOT_USER_ID")
                if not user_id:
                    raise ValueError("Cannot determine user_id")
            
            logger.info("poll_mentions: attempting Bearer Token method with user_id=%s", user_id)
            
            # Bearer Tokenを使って直接HTTPリクエスト
            url = f"https://api.twitter.com/2/users/{user_id}/mentions"
            headers = {
                "Authorization": f"Bearer {bearer_token}"
            }
            params = {
                "max_results": min(limit, 100),
                "tweet.fields": "created_at,author_id,conversation_id,text,reply_settings",
                "expansions": "author_id",
                "user.fields": "username"
            }
            if since_id:
                params["since_id"] = since_id
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tweets = data.get("data", [])
            users = {}
            if "includes" in data and "users" in data["includes"]:
                for u in data["includes"]["users"]:
                    users[u["id"]] = u.get("username")
            
            if tweets:
                logger.info("poll_mentions: Bearer Token method succeeded, got %d mentions", len(tweets))
                for t in tweets:
                    author_id = t.get("author_id")
                    yield {
                        "id": t.get("id"),
                        "text": t.get("text"),
                        "author_username": users.get(author_id) if author_id else None,
                        "reply_settings": t.get("reply_settings"),
                    }
                return
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning("poll_mentions: Bearer Token method failed with 401, falling back")
            else:
                logger.warning("poll_mentions: Bearer Token method failed: %s", e)
        except Exception as e:
            logger.warning("poll_mentions: Bearer Token method failed: %s", e)
    
    # Bearer Tokenが使えない、または失敗した場合は既存の方法を試す
    client = _create_client()
    try:
        me_resp = client.get_me()
        logger.info("poll_mentions: get_me() succeeded")
    except tweepy.TooManyRequests as e:
        logger.warning("poll_mentions: Twitter rate limit (get_me): %s", e)
        # レートリミット中は何も処理せず終了
        return
    except Exception as e:
        logger.error("poll_mentions: failed to get bot identity: %s", e, exc_info=True)
        return

    me = me_resp.data if me_resp is not None else None
    if me is None:
        logger.warning("poll_mentions: get_me returned empty response")
        return
    user_id = me["id"] if isinstance(me, dict) else me.id
    logger.info("poll_mentions: user_id=%s, attempting get_users_mentions", user_id)
    try:
        resp = client.get_users_mentions(
            id=user_id,
            since_id=since_id,
            max_results=min(limit, 100),
            expansions=["author_id"],
            user_fields=["username"],
            tweet_fields=["reply_settings"],
        )
        user_map = {}
        includes = getattr(resp, "includes", None)
        if includes and getattr(includes, "users", None):
            for u in includes["users"] if isinstance(includes, dict) else includes.users:
                uid = getattr(u, "id", None)
                uname = getattr(u, "username", None)
                if uid and uname:
                    user_map[uid] = uname
        for t in (resp.data or []):
            author_id = getattr(t, "author_id", None)
            reply_settings = getattr(t, "reply_settings", None)
            yield {
                "id": getattr(t, "id", None),
                "text": getattr(t, "text", None),
                "author_username": user_map.get(author_id),
                "reply_settings": reply_settings,
            }
        return
    except Exception as e:
        logger.warning("poll_mentions: get_users_mentions failed: %s", e)
        # Some tiers/apps cannot access mentions timeline.
        # Fallback to recent search with a simple query.
        handle = os.getenv("X_BOT_SCREEN_NAME", "govgovjapan")
        query = f"@{handle} -from:{handle}"
        try:
            # Prefer app-only bearer token for search if available
            bearer = os.getenv("X_BEARER_TOKEN")
            if bearer:
                app_client = tweepy.Client(bearer_token=bearer)
                # search_recent_tweets は max_results が 10〜100 必須
                resp = app_client.search_recent_tweets(
                    query=query,
                    max_results=max(10, min(limit, 100)),
                    since_id=since_id,
                    sort_order="recency",
                )
            else:
                resp = client.search_recent_tweets(
                    query=query,
                    max_results=max(10, min(limit, 100)),
                    since_id=since_id,
                    sort_order="recency",
                    expansions=["author_id"],
                    user_fields=["username"],
                    tweet_fields=["reply_settings"],
                )
            user_map = {}
            includes = getattr(resp, "includes", None)
            if includes and getattr(includes, "users", None):
                for u in includes["users"] if isinstance(includes, dict) else includes.users:
                    uid = getattr(u, "id", None)
                    uname = getattr(u, "username", None)
                    if uid and uname:
                        user_map[uid] = uname
            for t in (resp.data or []):
                author_id = getattr(t, "author_id", None)
                reply_settings = getattr(t, "reply_settings", None)
                yield {
                    "id": getattr(t, "id", None),
                    "text": getattr(t, "text", None),
                    "author_username": user_map.get(author_id),
                    "reply_settings": reply_settings,
                }
            return
        except Exception:
            # Final fallback: v1.1 mentions_timeline
            api = _create_api_v1()
            tweets = api.mentions_timeline(since_id=since_id, count=min(limit, 20), tweet_mode="extended")
            for t in tweets or []:
                yield {
                    "id": getattr(t, "id", None),
                    "text": getattr(t, "full_text", None) or getattr(t, "text", None),
                }


def run_loop(poll_interval_sec: int | None = None) -> None:
    """メンションのロングポーリング。

    参考レート（Per User/App）
      - mentions: 10/15min
      - search_recent: 60/15min
      - reverse_chronological: 5/15min

    既定では安全側に `MENTION_POLL_INTERVAL_SEC`（デフォルト90秒）を使用。
    """
    interval = poll_interval_sec or _get_interval("MENTION_POLL_INTERVAL_SEC", 90)
    last_id: Optional[str] = None
    while True:
        try:
            for tweet in poll_mentions(since_id=last_id):
                print(f"MENTION: {tweet['id']} | {tweet['text']}")
                last_id = tweet["id"]
        except Exception as e:
            print("LISTENER_ERROR:" + str(e))
        time.sleep(interval)


def build_sample_reply(original_text: str) -> str:
    """Return a sample reply until GCP-backed answer is ready."""
    template = os.getenv(
        "BOT_SAMPLE_REPLY",
        "ご連絡ありがとうございます。現在ベータ運用中です。正式回答は順次ご提供します。",
    )
    # 返信ツイートとして投稿するため、本文は定型文のみとする
    return template


def _sanitize_query_from_mention(text: str) -> str:
    """メンション文から検索クエリとして不要な要素を除去する。

    - 先頭・末尾の空白
    - アカウントメンション（@xxxx）
    - URL
    - 余分な連続空白
    """
    if not text:
        return ""
    # アカウントメンション除去
    cleaned = re.sub(r"@\w+", " ", text)
    # URL除去
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    # 空白を正規化
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text.strip()


def _compose_tweet_from_search_result(summary: str, sources: List[str], max_len: int | None = None) -> str:
    """検索結果からツイート本文を生成（URLは本文末尾に付与）。"""
    if max_len is None:
        max_len = _max_tweet_len()
    if not summary:
        return build_sample_reply("")

    def _normalize(text: str) -> str:
        """テキストを整形してTwitter投稿用に最適化する

        処理内容:
        1. 段落区切り（2つ以上の改行）を保護
        2. セクション見出し（【...】）の後に改行を追加
        3. 箇条書き記号の前に改行を追加
        4. 単一改行をスペースに変換（特殊記号の前後は保持）
        5. Markdown記法を除去
        6. URLの後に改行を追加
        7. 句読点・読点の後に改行を追加（読みやすさ向上）
        8. プレースホルダーを改行に戻す
        9. 連続改行/空白を正規化
        """
        # 1. 段落区切り（2つ以上の改行）を一時的にプレースホルダーで保護
        text = re.sub(r"\n{2,}", "<<PARAGRAPH_BREAK>>", text)

        # 2. セクション見出し（【...】, ▼...）の後ろに改行を追加
        text = re.sub(r"(【[^】]+】)\s*", r"\1\n", text)
        text = re.sub(r"(▼[^\n]{1,20})\s*", r"\1\n", text)

        # 3. 箇条書き記号（・, -, *, •）の処理
        # 行頭以外の箇条書きの前に改行を追加
        # ただし、スペース/コロン/句点の後にある箇条書きのみを対象（"庁舎管理・事務費"のような中黒は除外）
        text = re.sub(r"(?<!^)(?<!\n)([\s:：。])([\・\-\*\•])", r"\1\n\2", text, flags=re.MULTILINE)
        # 行頭の箇条書き記号の後にスペースがない場合は追加
        text = re.sub(r"^([\・\-\*\•])(?!\s)", r"\1 ", text, flags=re.MULTILINE)
        text = re.sub(r"\n([\・\-\*\•])(?!\s)", r"\n\1 ", text)

        # 4. 単一改行をスペースに変換（段落内の折り返しを解除）
        # ただし、セクション見出しや箇条書き、プレースホルダーの改行は保持
        lines = text.split("\n")
        result_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                result_lines.append(line)
                continue

            prev_line = lines[i - 1]
            # 前の行がセクション見出しで終わる、または現在の行が特殊記号で始まる、またはプレースホルダーの場合は改行を保持
            if (prev_line.rstrip().endswith(("】", "▼情報源", "▼")) or
                line.startswith(("・", "-", "*", "•", "【", "▼", "<<PARAGRAPH_BREAK>>")) or
                prev_line == "<<PARAGRAPH_BREAK>>"):
                result_lines.append("\n" + line)
            else:
                # それ以外は空白で結合
                result_lines.append(" " + line)

        text = "".join(result_lines)

        # 5. Markdownの強調記号 ** や * を除去
        text = text.replace("**", "")
        text = re.sub(r"\*([^\*\n]+?)\*", r"\1", text)

        # 6. URLの後に改行を追加（日本語文字の直前で切る）
        text = re.sub(r"(https?://[^\s\u3000-\u9fff\uff00-\uffef]+)", r"\1\n", text)

        # 7. 文末記号の後に改行を追加（ただし既に改行がある場合は追加しない）
        # 注: 「、」は文中の区切りなので改行しない
        parts = re.split(r"(。|！|!|？|\?)", text)
        result_parts = []
        for i, part in enumerate(parts):
            result_parts.append(part)
            # 文末記号の後で、次のパートがあり、改行で始まらない場合に改行を追加
            if part in ["。", "！", "!", "？", "?"] and i + 1 < len(parts):
                next_part = parts[i + 1] if i + 1 < len(parts) else ""
                if next_part and not next_part.startswith("\n") and not next_part.startswith("<<PARAGRAPH_BREAK>>"):
                    result_parts.append("\n")
        text = "".join(result_parts)

        # 8. プレースホルダーを実際の改行に戻す
        text = text.replace("<<PARAGRAPH_BREAK>>", "\n\n")

        # 9. 連続改行/空白の正規化
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    base = _normalize(summary)

    # sources からURLのみ抽出（タイトル等は除外）
    url_pat = re.compile(r"https?://\S+")
    url_candidates: List[str] = []
    for s in sources or []:
        if not s:
            continue
        if isinstance(s, str):
            m = url_pat.search(s)
            if m:
                url_candidates.append(m.group(0))
        elif isinstance(s, dict):
            u = s.get("uri") or s.get("link")
            if isinstance(u, str) and url_pat.match(u):
                url_candidates.append(u)
    # 重複除去
    seen = set()
    urls: List[str] = []
    for u in url_candidates:
        if u not in seen:
            seen.add(u)
            urls.append(u)

    if len(base) <= max_len:
        if urls:
            suffix_head = " 出典: "
            text = base
            # できる限り多くのURLを後ろに詰める
            if len(text) + len(suffix_head) <= max_len:
                text += suffix_head
                for u in urls:
                    add = (" " if not text.endswith(" ") else "") + u
                    if len(text) + len(add) <= max_len:
                        text += add
                    else:
                        break
            return text
        return base

    # 長すぎる場合は省略記号を付けて切り詰め
    if max_len <= 1:
        return base[:max_len]
    return base[: max_len - 1] + "…"


def _compose_sources_tweet(sources: List[str], max_len: int | None = None, max_items: int = 3) -> Optional[str]:
    """出典だけのスレッド用ツイートを生成する。

    先頭に「出典:」を置き、上位max_items件を列挙。URL優先で表示。
    文字数に収まらない場合は件数を減らして調整する。
    """
    if max_len is None:
        max_len = _max_tweet_len()
    cleaned: List[str] = []
    for s in sources:
        if not s:
            continue
        # タイトルよりURLを優先的に使う
        cleaned.append(str(s).strip())
    # 重複除去
    seen = set()
    unique = []
    for s in cleaned:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    # 上位から最大max_items件
    unique = unique[: max_items]
    if not unique:
        return None
    # 収まるまで件数を減らす
    while unique:
        body = "出典:\n" + "\n".join([f"- {u}"[:120] for u in unique])
        if len(body) <= max_len:
            return body
        unique = unique[:-1]
    return None


def build_search_reply(original_text: str) -> str:
    """Vertex AI Searchは使用しません。RAG Engineのみ使用します。
    
    この関数は後方互換性のために残していますが、build_rag_replyを呼び出します。
    """
    return build_rag_reply(original_text)


def build_rag_reply(original_text: str, *, return_metadata: bool = False) -> str | Dict[str, Any]:
    """Vertex AI RAG Engine を使って返信文を生成する。

    期待する環境変数:
      - PROJECT_ID
      - RAG_LOCATION（デフォルト: RAG_CORPUS_RESOURCE_NAMEから抽出、またはus-east4）
      - RAG_CORPUS_RESOURCE_NAME（projects/.../locations/.../ragCorpora/...）
      - MODEL_NAME（例: gemini-2.0-flash-exp）
    未設定の場合はサンプル返信にフォールバック。
    """
    truncated = False
    blocked = False
    fallback_used = False
    status = "ok"
    error_message: Optional[str] = None
    finish_reason: Optional[str] = None
    generation_config: Optional[Dict[str, Any]] = None
    raw_answer = ""
    final_answer = ""

    try:
        _load_env()
        project_id = os.getenv("PROJECT_ID")
        rag_corpus_resource_name = os.getenv("RAG_CORPUS_RESOURCE_NAME")
        model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
        
        # RAG_LOCATIONが設定されていない場合、RAG_CORPUS_RESOURCE_NAMEから抽出を試みる
        rag_location = os.getenv("RAG_LOCATION") or os.getenv("LOCATION")
        if not rag_location and rag_corpus_resource_name:
            # RAG_CORPUS_RESOURCE_NAMEの形式: projects/.../locations/.../ragCorpora/...
            import re
            match = re.search(r"/locations/([^/]+)/", rag_corpus_resource_name)
            if match:
                # RAG Corpusの実際のリージョンをそのまま使用（us-east4など）
                rag_location = match.group(1)
        
        # デフォルトはus-east4（RAG Corpusのリージョンに合わせる）
        rag_location = rag_location or "us-east4"

        if not project_id or not rag_corpus_resource_name:
            status = "missing_config"
            fallback_used = True
            final_answer = build_sample_reply(original_text)
            if return_metadata:
                return {
                    "answer": final_answer,
                    "raw_answer": raw_answer,
                    "status": status,
                    "finish_reason": finish_reason,
                    "truncated": truncated,
                    "blocked": blocked,
                    "fallback_used": fallback_used,
                    "error": "Missing PROJECT_ID or RAG_CORPUS_RESOURCE_NAME",
                    "generation_config": generation_config,
                }
            return final_answer

        client = VertexAIRAGClientNew(
            project_id=project_id,
            location=rag_location,
            rag_corpus_resource_name=rag_corpus_resource_name,
            model_name=model_name,
            top_k=10,  # より多くの関連文書を取得して詳細な予算データを引き出す
            max_output_tokens=int(os.getenv("RAG_MAX_OUTPUT_TOKENS", "4096")),  # 回答が途中で切れないように増やす
        )

        # factcheck_prompt.pyのプロンプトを使用
        user_query = _sanitize_query_from_mention(original_text) or original_text or "行政事業レビューについて"
        instruction = build_factcheck_instruction(user_query)
        result = client.generate_answer(query=instruction) or {}

        raw_answer = (result.get("answer") or "").strip()
        finish_reason = result.get("finish_reason")
        truncated = bool(result.get("truncated"))
        blocked = bool(result.get("blocked"))
        generation_config = result.get("generation_config")
        status = result.get("status") or ("truncated" if truncated else "ok")

        # finish_reasonがMAX_TOKENSの場合は回答が途中で切れている
        finish_reason_str = str(finish_reason).upper() if finish_reason else ""
        is_max_tokens = "MAX_TOKENS" in finish_reason_str or finish_reason_str == "2"
        
        if is_max_tokens:
            logger.warning(f"Answer truncated due to MAX_TOKENS: finish_reason={finish_reason}, answer_length={len(raw_answer)}")
            truncated = True
            status = "truncated"

        if raw_answer:
            # Web アプリ用なので文字数制限を大きくして切り詰めを防ぐ
            final_answer = _compose_tweet_from_search_result(raw_answer, sources=[], max_len=100000)
            # 回答が途中で切れている場合は末尾に注記を追加
            if truncated and is_max_tokens:
                # 既に末尾に「…」が付いている場合は追加しない
                if not final_answer.endswith("…"):
                    final_answer += "（回答が途中で切れています）"
        else:
            status = "empty"

        if blocked and not final_answer:
            fallback_used = True
            final_answer = build_sample_reply(original_text)

    except VertexAIRAGError as e:
        error_message = str(e)
        if "429" in error_message or "rate_limit" in error_message.lower() or "resource exhausted" in error_message.lower():
            status = "rate_limited"
            logger.warning("RAG reply error: Rate limited (429) - %s", error_message)
            # レート制限の場合は返信を送らない（別のリージョンで成功した場合のみ返信）
            # final_answerは空のままにして、呼び出し側で判定できるようにする
        elif "404" in error_message or "not found" in error_message.lower():
            status = "model_not_found"
            logger.error("RAG reply error: Model not found (404) - %s", error_message)
        else:
            status = "error"
            logger.warning("RAG reply error: %s", error_message)
    except Exception as e:
        error_message = str(e)
        status = "error"
        logger.error("Unexpected RAG reply error: %s", error_message, exc_info=True)

    # レート制限の場合はフォールバックしない（返信を送らない）
    if not final_answer and status != "rate_limited":
        fallback_used = True
        final_answer = build_sample_reply(original_text)

    if return_metadata:
        return {
            "answer": final_answer,
            "raw_answer": raw_answer,
            "status": status,
            "finish_reason": finish_reason,
            "truncated": truncated,
            "blocked": blocked,
            "fallback_used": fallback_used,
            "error": error_message,
            "generation_config": generation_config,
        }

    if status != "ok":
        print(f"RAG_REPLY_ERROR:status={status}:error={error_message}")

    return final_answer


def reply_to_latest_mention(dry_run: bool = True) -> Dict[str, Any]:
    """Reply to the most recent mention with a sample text.
    
    この関数は後方互換性のために残していますが、RAG Engineのみを使用します。

    Parameters
    ----------
    dry_run: bool
        If True, do not post; return the would-be payload instead.
    """
    from .twitter_poster import post_tweet  # lazy import to avoid circulars

    # 直近のメンションから「返信許可=全員」優先で選別
    items = list(poll_mentions(limit=10))
    def is_reply_open(it: dict) -> bool:
        rs = it.get("reply_settings")
        # None or 'everyone' を許可とみなす
        return (rs is None) or (str(rs).lower() == "everyone")

    items_sorted = [it for it in items if is_reply_open(it)] or items
    items_sorted = items_sorted[:1]
    items = items_sorted
    if not items:
        return {"ok": False, "reason": "no_mentions"}
    latest = items[0]
    
    # スレッド全体を取得してRAG Engineで回答生成
    tid = str(latest.get("id"))
    conv_text = fetch_conversation_text(tid)
    base_text = conv_text or latest.get("text") or ""
    reply_result = build_rag_reply(base_text, return_metadata=True)
    
    # メタデータから回答とステータスを取得
    if isinstance(reply_result, dict):
        reply_text = reply_result.get("answer", "")
        reply_status = reply_result.get("status", "ok")
    else:
        reply_text = reply_result or ""
        reply_status = "ok"
    
    # レート制限の場合は返信を送らない
    if reply_status == "rate_limited":
        logger.info("Skipping reply due to rate limit (429). Will retry on next schedule.")
        return {"ok": True, "reason": "rate_limited", "target": latest}

    # 一時運用: 通常投稿のみ（メンションは付けない）。
    # 可能なら会話スレッド本文を取得し、その内容で検索/RAGを強化する設計に拡張可能。
    # ここでは reply_text をそのまま使用。
    author_username = latest.get("author_username")
    final_text = reply_text

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "reply_to": latest["id"],
            "text": final_text,
            "sources_text": None,
            "mention": f"@{author_username}" if author_username else None,
            "mode": "post_only",
        }

    data = post_tweet(text=final_text)
    return {"ok": True, "dry_run": False, "data": data}


if __name__ == "__main__":
    run_loop()



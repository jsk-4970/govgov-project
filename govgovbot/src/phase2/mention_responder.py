import os
import sqlite3
import time
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv

if __package__ in (None, ""):
    import sys

    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    _PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    __package__ = "src.phase2"

# 既存ポスター（フォールバック用）
from .twitter_poster import post_tweet as tweepy_post_tweet, create_tweepy_client


# 固定値（要件）
BOT_ID = "1974382229284655104"
BOT_USERNAME = "govgovjapan"
API_BASE = os.getenv("X_API_BASE", "https://api.x.com/2")


# SQLite（ローカル永続）
DB_PATH = os.getenv("STATE_DB_PATH", os.path.join(os.getcwd(), "state.db"))


def _load_env() -> None:
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
    # Secret Managerから認証情報をロード（環境変数が未設定の場合）
    try:
        from src.common.secret_manager import load_secrets_to_env
        load_secrets_to_env()
    except Exception as e:
        print(f"SECRET_MANAGER_LOAD_ERROR: {e}")


def _utc_now_ts() -> int:
    return int(time.time())


def _ensure_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_mentions (
                mention_id TEXT PRIMARY KEY,
                reply_tweet_id TEXT,
                ts INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conv_index (
                conversation_id TEXT PRIMARY KEY,
                last_bot_tweet_id TEXT,
                last_bot_created_at TEXT,
                ts INTEGER
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_checkpoint(key: str) -> Optional[str]:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM checkpoints WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _set_checkpoint(key: str, value: str) -> None:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO checkpoints(key, value) VALUES(?,?)\n             ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_processed_mention_if_absent(mention_id: str) -> bool:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO processed_mentions(mention_id, ts) VALUES(?,?)",
            (mention_id, _utc_now_ts()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _update_processed_reply(mention_id: str, reply_tweet_id: str) -> None:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE processed_mentions SET reply_tweet_id=?, ts=? WHERE mention_id=?",
            (reply_tweet_id, _utc_now_ts(), mention_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_conv_index(conversation_id: str) -> Optional[Dict[str, Any]]:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT last_bot_tweet_id, last_bot_created_at, ts FROM conv_index WHERE conversation_id=?",
            (conversation_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "last_bot_tweet_id": row[0],
            "last_bot_created_at": row[1],
            "ts": row[2],
        }
    finally:
        conn.close()


def _upsert_conv_index(conversation_id: str, last_bot_tweet_id: Optional[str], last_bot_created_at: Optional[str]) -> None:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO conv_index(conversation_id, last_bot_tweet_id, last_bot_created_at, ts)
            VALUES(?,?,?,?)
            ON CONFLICT(conversation_id) DO UPDATE SET
              last_bot_tweet_id=excluded.last_bot_tweet_id,
              last_bot_created_at=excluded.last_bot_created_at,
              ts=excluded.ts
            """,
            (conversation_id, last_bot_tweet_id, last_bot_created_at, _utc_now_ts()),
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------------
# HTTP ユーティリティ（リトライ/429待機）
# -----------------------------


def _get_oauth2_user_token() -> Optional[str]:
    # OAuth 2.0 (User context; Authorization Code with PKCE)
    tok = os.getenv("OAUTH2_ACCESS_TOKEN")
    return tok.strip() if tok else None


def _get_app_bearer_token() -> Optional[str]:
    # App-only bearer (for search等)
    tok = os.getenv("X_BEARER_TOKEN")
    return tok.strip() if tok else None


def _sleep_until_reset_or(seconds: int) -> None:
    try:
        time.sleep(max(1, int(seconds)))
    except Exception:
        time.sleep(30)


def _request_with_retry(
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> Optional[requests.Response]:
    session = requests.Session()
    backoff = 1
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.request(method=method, url=url, headers=headers, params=params, json=json_body, timeout=30)
        except Exception as e:
            if attempt >= max_retries:
                print(f"HTTP_ERROR:{method} {url} attempt={attempt} err={e}")
                return None
            time.sleep(backoff)
            backoff *= 2
            continue

        # 成功
        if 200 <= resp.status_code < 300:
            return resp

        # 429
        if resp.status_code == 429:
            reset = resp.headers.get("x-rate-limit-reset") or resp.headers.get("X-Rate-Limit-Reset")
            if reset:
                try:
                    wait = max(0, int(reset) - int(time.time())) + 1
                except Exception:
                    wait = 60
            else:
                wait = 60
            print(f"RATE_LIMIT_429:{method} {url} wait={wait}s")
            _sleep_until_reset_or(wait)
            continue

        # 5xx -> バックオフ
        if 500 <= resp.status_code < 600:
            if attempt >= max_retries:
                print(f"HTTP_5XX:{method} {url} status={resp.status_code} body={resp.text[:300]}")
                return resp
            time.sleep(backoff)
            backoff *= 2
            continue

        # 4xx -> ログ出力してスキップ
        print(f"HTTP_4XX:{method} {url} status={resp.status_code} body={resp.text[:300]}")
        return resp

    return None


# -----------------------------
# API 実装
# -----------------------------


def _fetch_mentions_since(since_id: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """GET /2/users/:id/mentions をページングしつつ差分取得。

    Returns
    -------
    (mentions, newest_id)
      mentions: data配列の要素（必要フィールドのみ）
      newest_id: APIが返す最も新しいID（str）
    """
    user_id = BOT_ID  # BOTの固定IDを利用

    token = _get_oauth2_user_token()
    if not token:
        # Tweepy フォールバック
        try:
            client = create_tweepy_client()
        except Exception as exc:
            raise RuntimeError("OAUTH2_ACCESS_TOKEN 未設定かつ Tweepy クライアント作成に失敗しました") from exc

        params_fields = ["author_id", "created_at", "conversation_id", "referenced_tweets"]

        all_items: List[Dict[str, Any]] = []
        newest_id_val: Optional[str] = None
        pagination_token: Optional[str] = None

        while True:
            resp = client.get_users_mentions(
                id=user_id,
                since_id=since_id,
                max_results=100,
                tweet_fields=params_fields,
                pagination_token=pagination_token,
            )
            data = resp.data or []
            meta = getattr(resp, "meta", {}) or {}
            if not newest_id_val:
                newest_id_val = meta.get("newest_id") if isinstance(meta, dict) else getattr(meta, "newest_id", None)
            for t in data:
                all_items.append({
                    "id": str(getattr(t, "id", None)),
                    "text": getattr(t, "text", None),
                    "author_id": str(getattr(t, "author_id", None)) if getattr(t, "author_id", None) is not None else None,
                    "created_at": getattr(t, "created_at", None).isoformat().replace("+00:00", "Z") if getattr(t, "created_at", None) else None,
                    "conversation_id": str(getattr(t, "conversation_id", None)) if getattr(t, "conversation_id", None) is not None else None,
                    "referenced_tweets": [
                        {"type": getattr(rt, "type", None), "id": str(getattr(rt, "id", None))}
                        for rt in (getattr(t, "referenced_tweets", None) or [])
                    ],
                })
            pagination_token = meta.get("next_token") if isinstance(meta, dict) else getattr(meta, "next_token", None)
            if not pagination_token:
                break
        return all_items, newest_id_val

    # Raw HTTP (user OAuth2 bearer)
    url = f"{API_BASE}/users/{user_id}/mentions"
    headers = {"Authorization": f"Bearer {token}"}
    params: Dict[str, Any] = {
        "max_results": 100,
        "tweet.fields": "author_id,created_at,conversation_id,referenced_tweets",
    }
    if since_id:
        params["since_id"] = since_id

    all_data: List[Dict[str, Any]] = []
    newest_id_val: Optional[str] = None
    pagination_token: Optional[str] = None

    while True:
        local_params = dict(params)
        if pagination_token:
            local_params["pagination_token"] = pagination_token
        resp = _request_with_retry("GET", url, headers, params=local_params)
        if resp is None:
            raise RuntimeError("mentions API 呼び出しに失敗しました")
        if resp.status_code >= 400 and resp.status_code != 429:
            # 4xx/5xx は上位でスキップ
            print(f"MENTIONS_ERROR status={resp.status_code} body={resp.text[:300]}")
            break
        js = resp.json()
        if newest_id_val is None:
            newest_id_val = (js.get("meta") or {}).get("newest_id")
        for t in js.get("data", []) or []:
            # 必要フィールドだけに揃える
            all_data.append({
                "id": str(t.get("id")) if t.get("id") is not None else None,
                "text": t.get("text"),
                "author_id": str(t.get("author_id")) if t.get("author_id") is not None else None,
                "created_at": t.get("created_at"),
                "conversation_id": str(t.get("conversation_id")) if t.get("conversation_id") is not None else None,
                "referenced_tweets": t.get("referenced_tweets") or [],
            })
        pagination_token = (js.get("meta") or {}).get("next_token")
        if not pagination_token:
            break

    return all_data, newest_id_val


def _search_latest_bot_in_conversation(conversation_id: str) -> Tuple[Optional[str], Optional[str]]:
    """GET /2/tweets/search/recent で会話内のBot最新投稿を取得し、(tweet_id, created_at) を返す。

    未検出時は (None, None)。
    """
    token = _get_app_bearer_token() or _get_oauth2_user_token()
    if not token:
        # Tweepy フォールバック
        try:
            from .twitter_listener import _get_bearer_client, _create_client  # type: ignore
            client = _get_bearer_client() or _create_client()
            resp = client.search_recent_tweets(
                query=f"conversation_id:{conversation_id} from:{BOT_USERNAME}",
                max_results=100,
                tweet_fields=["created_at"],
                sort_order="recency",
            )
            data = resp.data or []
            if not data:
                return None, None
            # recency 指定で先頭が最新
            t0 = data[0]
            tid = str(getattr(t0, "id", None)) if getattr(t0, "id", None) is not None else None
            created_at = getattr(t0, "created_at", None)
            created_iso = created_at.isoformat().replace("+00:00", "Z") if created_at else None
            return tid, created_iso
        except Exception:
            return None, None

    url = f"{API_BASE}/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "query": f"conversation_id:{conversation_id} from:{BOT_USERNAME}",
        "max_results": 100,
        "tweet.fields": "created_at",
    }
    resp = _request_with_retry("GET", url, headers, params=params)
    if resp is None or resp.status_code >= 400 and resp.status_code != 429:
        return None, None
    js = resp.json()
    items = js.get("data") or []
    if not items:
        return None, None
    # 最も新しい created_at を選ぶ（ISOの辞書順比較でOK）
    latest = max(items, key=lambda x: x.get("created_at", ""))
    return str(latest.get("id")) if latest.get("id") is not None else None, latest.get("created_at")


def _post_reply_via_http(text: str, in_reply_to_tweet_id: str) -> Optional[Dict[str, Any]]:
    token = _get_oauth2_user_token()
    if not token:
        return None
    url = f"{API_BASE}/tweets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "reply": {"in_reply_to_tweet_id": str(in_reply_to_tweet_id)},
    }
    resp = _request_with_retry("POST", url, headers, json_body=body)
    if resp is None or resp.status_code >= 400 and resp.status_code != 429:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def _build_reply_text(original_text: str) -> str:
    """返信本文を生成（既存の関数があれば活用、無ければサンプル）。"""
    try:
        from .twitter_listener import build_search_reply  # type: ignore
        return build_search_reply(original_text) or "ご連絡ありがとうございます。現在ベータ運用中です。正式回答は順次ご提供します。"
    except Exception:
        return "ご連絡ありがとうございます。現在ベータ運用中です。正式回答は順次ご提供します。"


def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


def _should_skip_as_already_replied(mention: Dict[str, Any], conv_cache: Dict[str, Dict[str, Any]]) -> bool:
    author_id = _safe_str(mention.get("author_id"))
    if author_id == BOT_ID:
        return True  # 自分自身は対象外

    conv_id = _safe_str(mention.get("conversation_id")) or _safe_str(mention.get("id"))
    created_at = _safe_str(mention.get("created_at"))
    info = conv_cache.get(conv_id)
    if not info:
        return False
    last_bot_created_at = _safe_str(info.get("last_bot_created_at"))
    if not last_bot_created_at:
        return False
    # ISO8601の辞書順で比較可能（UTC前提）
    return created_at <= last_bot_created_at


def run_once(dry_run: bool = False) -> Dict[str, Any]:
    """メンション差分を取得し、要件に従って1回分の返信処理を行う（バッチ）。

    - 外部からのメンションのみ対象（author_id != BOT_ID）
    - conversation_id 毎に Bot の最新発言を conv_index で判定（未知は検索してキャッシュ）
    - 既返信と判定されたメンションはスキップ
    - `processed_mentions` への INSERT OR IGNORE で冪等化（存在時は即スキップ）
    - 返信成功時に `processed_mentions` と `conv_index` を更新
    - 429 は x-rate-limit-reset を見て待機（無ければ固定60秒）
    - ネットワーク/5xx は指数バックオフで最大3回リトライ
    - since_id は最後に成功時のみ更新
    """
    _load_env()
    _ensure_db()

    since_id = _get_checkpoint("mentions_since")
    had_unhandled_error = False
    try:
        mentions, newest_id = _fetch_mentions_since(since_id)
    except Exception as e:
        print(f"FETCH_MENTIONS_ERROR:{e}")
        return {"ok": False, "error": str(e)}

    # 外部からのメンションだけ対象にする
    targets = [m for m in (mentions or []) if _safe_str(m.get("author_id")) != BOT_ID]
    if not targets:
        # 取得成功時のみ since_id を前進
        if newest_id:
            _set_checkpoint("mentions_since", str(newest_id))
        return {"ok": True, "reason": "no_external_mentions", "fetched": len(mentions or []), "processed": 0}

    # conversation_id をキーにグループ化
    conv_ids: List[str] = []
    for m in targets:
        cid = _safe_str(m.get("conversation_id")) or _safe_str(m.get("id"))
        if cid and cid not in conv_ids:
            conv_ids.append(cid)

    # conv_index キャッシュの準備（未知のみ recent search）
    conv_cache: Dict[str, Dict[str, Any]] = {}
    for cid in conv_ids:
        info = _get_conv_index(cid)
        if info:
            conv_cache[cid] = info
            continue
        tid, created = _search_latest_bot_in_conversation(cid)
        conv_cache[cid] = {"last_bot_tweet_id": tid, "last_bot_created_at": created}
        _upsert_conv_index(cid, tid, created)

    # created_at 昇順で安定化（古いものから）
    def _iso(x: Dict[str, Any]) -> str:
        return _safe_str(x.get("created_at"))

    targets_sorted = sorted(targets, key=_iso)

    processed = 0
    skipped_already = 0
    skipped_duplicate = 0
    reply_errors = 0

    for m in targets_sorted:
        cid = _safe_str(m.get("conversation_id")) or _safe_str(m.get("id"))
        mid = _safe_str(m.get("id"))
        if not mid:
            continue

        # 既返信スキップ（会話内 Bot の最新発言 <= メンション時刻）
        try:
            if _should_skip_as_already_replied(m, conv_cache):
                skipped_already += 1
                continue
        except Exception:
            # 失敗時は安全側（返信に進む）
            pass

        # 冪等化：事前に processed_mentions へ INSERT OR IGNORE
        inserted = False
        try:
            inserted = _insert_processed_mention_if_absent(mid)
        except Exception as e:
            print(f"PROCESSED_MENTION_INSERT_ERROR:{mid}:{e}")
            had_unhandled_error = True
            continue

        if not inserted:
            # 既に処理済み（二重返信防止）
            skipped_duplicate += 1
            continue

        # 返信本文を決定
        text = _build_reply_text(_safe_str(m.get("text")))

        if dry_run:
            processed += 1
            # conv_index を即時更新（API反映遅延に依存しない）
            reply_created_at = _safe_str(m.get("created_at"))
            _upsert_conv_index(cid, last_bot_tweet_id=f"dry-{mid}", last_bot_created_at=reply_created_at)
            conv_cache[cid] = {
                "last_bot_tweet_id": f"dry-{mid}",
                "last_bot_created_at": reply_created_at,
            }
            continue

        # POST /2/tweets（HTTP → 失敗時 Tweepy フォールバック）
        try:
            posted = _post_reply_via_http(text=text, in_reply_to_tweet_id=mid)
            if not posted:
                # Tweepy でフォールバック
                data = tweepy_post_tweet(text=text, in_reply_to_tweet_id=mid)
                # Tweepy は {"id": "...", ...} を返す実装
                reply_id = _safe_str((data or {}).get("id"))
                reply_created = None  # Tweepyはcreated_at未付与のことが多い
            else:
                data = posted.get("data") or {}
                reply_id = _safe_str(data.get("id"))
                reply_created = _safe_str(data.get("created_at")) or _safe_str(m.get("created_at"))

            if reply_id:
                _update_processed_reply(mid, reply_id)
                latest_created = reply_created or _safe_str(m.get("created_at"))
                _upsert_conv_index(cid, reply_id, latest_created)
                conv_cache[cid] = {
                    "last_bot_tweet_id": reply_id,
                    "last_bot_created_at": latest_created,
                }
                processed += 1
            else:
                reply_errors += 1
        except Exception as e:
            # 4xx はログ出力してスキップ
            print(f"POST_REPLY_ERROR:{mid}:{e}")
            reply_errors += 1
            # since_id は最後に成功時のみ更新するため、ここでは何もしない
            continue

    # バッチ成功時のみ since_id を更新（再取得は行わず、最初に受け取った newest_id を利用）
    if processed >= 0 and not had_unhandled_error:
        newest = newest_id
        if not newest:
            # フォールバック: 今回取得した全メンションの中で最大ID
            try:
                def _as_int(s: Optional[str]) -> int:
                    try:
                        return int(s or "0")
                    except Exception:
                        return 0

                max_id = max((_as_int(_safe_str(m.get("id"))) for m in (mentions or [])), default=0)
                newest = str(max_id) if max_id > 0 else None
            except Exception:
                newest = None
        if newest:
            _set_checkpoint("mentions_since", newest)

    return {
        "ok": True,
        "processed": processed,
        "skipped_existing_conversation": skipped_already,
        "skipped_already_processed": skipped_duplicate,
        "reply_errors": reply_errors,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Process new mentions once and reply idempotently.")
    parser.add_argument("--dry-run", action="store_true", help="Do not post; simulate only.")
    args = parser.parse_args()
    try:
        result = run_once(dry_run=bool(args.dry_run))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

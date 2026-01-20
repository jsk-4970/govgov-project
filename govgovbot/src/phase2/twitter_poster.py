import os
import sys
import time
import argparse
from collections import deque
from typing import Optional, Dict, Any

from dotenv import load_dotenv
import tweepy


def load_environment(dotenv_path: Optional[str] = None) -> None:
    """Load environment variables from a .env file.

    Parameters
    ----------
    dotenv_path: Optional[str]
        Explicit .env path. If omitted, uses current working directory.
    """
    if dotenv_path is None:
        dotenv_path = os.path.join(os.getcwd(), ".env")
    load_dotenv(dotenv_path=dotenv_path)
    # Secret Managerから認証情報をロード（環境変数が未設定の場合）
    try:
        from src.common.secret_manager import load_secrets_to_env
        load_secrets_to_env()
    except Exception as e:
        print(f"SECRET_MANAGER_LOAD_ERROR: {e}")


def ensure_required_env_vars_present() -> None:
    """Validate that all required X API credentials are present in env.

    Raises
    ------
    RuntimeError
        If any required variable is missing.
    """
    required_vars = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ",".join(missing)
        )


def create_tweepy_client() -> tweepy.Client:
    """Create a Tweepy v2 Client using OAuth 1.0a user context credentials.

    Returns
    -------
    tweepy.Client
        Authenticated client capable of posting tweets on behalf of the user.
    """
    # Always load .env explicitly to avoid shell variance
    load_environment()

    # Prefer OAuth2 token if provided
    oauth2_token = os.getenv("OAUTH2_ACCESS_TOKEN")
    if oauth2_token:
        return tweepy.Client(bearer_token=None, access_token=oauth2_token)
    ensure_required_env_vars_present()
    client = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )
    return client


# ---------------------------
# Throttling (simple client-side)
# ---------------------------
_POST_TIMES_MIN = deque()  # last 60 seconds
_POST_TIMES_HOUR = deque()  # last 3600 seconds
_LAST_POST_AT = 0.0


def _throttle_before_post() -> None:
    """Apply simple rate limits based on env settings.

    Env:
      - POST_MIN_INTERVAL_SEC (default: 60)
      - POST_MAX_PER_MINUTE (default: 8)
      - POST_MAX_PER_HOUR (default: 200)
    """
    global _LAST_POST_AT
    now = time.time()
    min_interval = float(os.getenv("POST_MIN_INTERVAL_SEC", "60"))
    max_per_minute = int(os.getenv("POST_MAX_PER_MINUTE", "8"))
    max_per_hour = int(os.getenv("POST_MAX_PER_HOUR", "200"))

    # Enforce min interval
    since = now - _LAST_POST_AT
    if since < min_interval:
        time.sleep(min_interval - since)
        now = time.time()

    # Clean old timestamps
    cutoff_min = now - 60
    cutoff_hour = now - 3600
    while _POST_TIMES_MIN and _POST_TIMES_MIN[0] < cutoff_min:
        _POST_TIMES_MIN.popleft()
    while _POST_TIMES_HOUR and _POST_TIMES_HOUR[0] < cutoff_hour:
        _POST_TIMES_HOUR.popleft()

    # Enforce per-minute/hour caps
    if len(_POST_TIMES_MIN) >= max_per_minute:
        sleep_s = (_POST_TIMES_MIN[0] + 60) - now
        if sleep_s > 0:
            time.sleep(sleep_s)
    if len(_POST_TIMES_HOUR) >= max_per_hour:
        sleep_s = (_POST_TIMES_HOUR[0] + 3600) - now
        if sleep_s > 0:
            time.sleep(sleep_s)

    # record (after sleeps)
    now = time.time()
    _POST_TIMES_MIN.append(now)
    _POST_TIMES_HOUR.append(now)
    _LAST_POST_AT = now


def post_tweet(
    text: str,
    in_reply_to_tweet_id: Optional[str] = None,
    quote_tweet_id: Optional[str] = None,
    skip_throttle: bool = False,
) -> Dict[str, Any]:
    """Post a tweet.

    Parameters
    ----------
    text: str
        The tweet text to publish.
    in_reply_to_tweet_id: Optional[str]
        If provided, the new tweet will be a reply to this tweet ID.

    Returns
    -------
    Dict[str, Any]
        Response data returned by Tweepy/HTTP API.
    """
    # Throttle to avoid rate limits (can be disabled for batch processing)
    if not skip_throttle:
        _throttle_before_post()
    client = create_tweepy_client()
    try:
        if quote_tweet_id:
            response = client.create_tweet(text=text, quote_tweet_id=quote_tweet_id)
        elif in_reply_to_tweet_id:
            response = client.create_tweet(text=text, in_reply_to_tweet_id=in_reply_to_tweet_id)
        else:
            response = client.create_tweet(text=text)
        # TweepyのResponseオブジェクトからdataを取得
        data = getattr(response, "data", None)
        if data is None:
            return {}
        # Tweetオブジェクトの場合は辞書に変換
        if hasattr(data, "id"):
            return {
                "id": str(getattr(data, "id", None)) if getattr(data, "id", None) is not None else None,
                "text": getattr(data, "text", None),
            }
        # 既に辞書の場合はそのまま返す
        if isinstance(data, dict):
            return data
        # その他の場合は空辞書を返す
        return {}
    except tweepy.Forbidden as e:
        # 403エラー（レートリミットなど）の場合、特定のメッセージを返す
        error_msg = str(e).lower()
        if "403" in error_msg or "rate limit" in error_msg or "forbidden" in error_msg:
            raise RuntimeError("申し訳ありません。APIのレートリミットです。時間を空けてお試しください。") from e
        # その他の403エラー
        detail = None
        try:
            if hasattr(e, "response") and hasattr(e.response, "text"):
                detail = e.response.text
        except Exception:
            pass
        raise RuntimeError(f"FORBIDDEN: {detail or str(e)}") from e


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Post a tweet via Tweepy client.")
    parser.add_argument(
        "--text",
        required=True,
        help="Tweet text to publish.",
    )
    parser.add_argument(
        "--reply-to",
        dest="reply_to",
        default=None,
        help="Optional tweet ID to reply to.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate credentials and show intent, but do not post.",
    )
    return parser


def main() -> int:
    load_environment()
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.dry_run:
        try:
            create_tweepy_client()
            print("DRY_RUN_OK: credentials look fine; tweet not posted")
            return 0
        except Exception as e:
            print("DRY_RUN_ERROR:" + str(e))
            return 2

    try:
        data = post_tweet(text=args.text, in_reply_to_tweet_id=args.reply_to)
        print("OK:" + str(data))
        return 0
    except Exception as e:
        print("ERROR:" + str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())




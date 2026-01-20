import os
import sys
from dotenv import load_dotenv
import tweepy


def main() -> int:
    # 明示的に .env を指定（stdin 実行時の不具合回避）
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

    required_vars = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    ]
    missing = [k for k in required_vars if not os.getenv(k)]
    if missing:
        print("MISSING_ENV:" + ",".join(missing))
        return 2

    client = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )

    text = os.getenv("X_TEST_TWEET_TEXT", "テスト投稿 from govgov ✅")
    try:
        resp = client.create_tweet(text=text)
        print("OK:" + str(resp.data))
        return 0
    except Exception as e:
        print("ERROR:" + str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())

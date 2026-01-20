#!/usr/bin/env python3
"""
X (Twitter) OAuth 2.0 Authorization Code (with PKCE) login helper.

- 事前に以下の環境変数を .env に設定してください:
  - OAUTH2_CLIENT_ID
  - OAUTH2_CLIENT_SECRET (任意。機密クライアントの場合)
  - OAUTH2_REDIRECT_URI (例: http://127.0.0.1:8765/callback)
  - OAUTH2_SCOPES (省略時: tweet.read tweet.write users.read offline.access)

実行するとローカルに簡易HTTPサーバーを立て、ブラウザで認可URLを開きます。
認可が完了するとアクセストークンとリフレッシュトークンを取得し、
標準出力に表示するとともに .env に追記します:

  OAUTH2_ACCESS_TOKEN=...
  OAUTH2_REFRESH_TOKEN=...

注意: 取得したトークンはユーザー文脈の投稿に使用されます。
"""

import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from dotenv import load_dotenv
import tweepy


def load_env() -> None:
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))


def write_env_tokens(access_token: str, refresh_token: str) -> None:
    env_path = Path(".env")
    text = []
    if env_path.exists():
        text.append(env_path.read_text(encoding="utf-8"))
        if not text[-1].endswith("\n"):
            text.append("\n")
    text.append(f"OAUTH2_ACCESS_TOKEN={access_token}\n")
    if refresh_token:
        text.append(f"OAUTH2_REFRESH_TOKEN={refresh_token}\n")
    env_path.write_text("".join(text), encoding="utf-8")


def get_oauth2_handler() -> tweepy.OAuth2UserHandler:
    # Allow both OAUTH2_* and X_* env names
    client_id = os.getenv("OAUTH2_CLIENT_ID") or os.getenv("X_CLIENT_ID")
    client_secret = os.getenv("OAUTH2_CLIENT_SECRET") or os.getenv("X_CLIENT_SECRET")
    redirect_uri = (
        os.getenv("OAUTH2_REDIRECT_URI")
        or os.getenv("X_REDIRECT_URI")
        or "http://127.0.0.1:8765/callback"
    )
    scopes = (
        os.getenv("OAUTH2_SCOPES")
        or os.getenv("X_OAUTH2_SCOPES")
        or "tweet.read tweet.write users.read offline.access"
    ).split()
    if not client_id:
        print("Missing OAUTH2_CLIENT_ID in .env", file=sys.stderr)
        sys.exit(2)
    return tweepy.OAuth2UserHandler(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scopes,
        client_secret=client_secret,
    )


def run_local_server_and_fetch_token(handler: tweepy.OAuth2UserHandler) -> tuple[str, str]:
    redirect_uri = handler.redirect_uri
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8765

    auth_url = handler.get_authorization_url()
    print("Open this URL in your browser to authorize:\n" + auth_url)

    auth_response_holder = {"url": None}

    class _Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            # 保存してすぐ応答
            full_url = f"http://{host}:{port}{self.path}"
            auth_response_holder["url"] = full_url
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Authorization received. You may close this tab.")

        def log_message(self, fmt, *args):
            return  # quiet

    httpd = HTTPServer((host, port), _Callback)
    print(f"Waiting for callback at {redirect_uri} ...")

    # ポーリングで待機（最大5分）
    start = time.time()
    while time.time() - start < 300:
        httpd.handle_request()
        if auth_response_holder["url"]:
            break

    if not auth_response_holder["url"]:
        print("Timeout waiting for authorization response", file=sys.stderr)
        sys.exit(3)

    token = handler.fetch_token(authorization_response=auth_response_holder["url"])  # type: ignore[arg-type]
    access_token = token.get("access_token", "")
    refresh_token = token.get("refresh_token", "")
    if not access_token:
        print("Failed to obtain access token", file=sys.stderr)
        sys.exit(4)
    return access_token, refresh_token


def main() -> int:
    load_env()
    handler = get_oauth2_handler()
    access_token, refresh_token = run_local_server_and_fetch_token(handler)
    print("\nACCESS_TOKEN=", access_token)
    if refresh_token:
        print("REFRESH_TOKEN=", refresh_token)
    write_env_tokens(access_token, refresh_token)
    print("\nSaved tokens to .env (OAUTH2_ACCESS_TOKEN / OAUTH2_REFRESH_TOKEN)")
    return 0


if __name__ == "__main__":
    sys.exit(main())



import json
from typing import Any

import functions_framework
from flask import Request, jsonify


@functions_framework.http
def reply_latest_http(request: Request) -> Any:
    """Cloud Functions(Gen2) HTTP handler to reply to the latest mention once.

    Query params:
      - dry_run: 1/true/yes to avoid posting (default: false)
    """
    from src.phase2.twitter_listener import reply_to_latest_mention_replying

    dry_param = (request.args.get("dry_run", "0") or "0").lower()
    dry = dry_param in ("1", "true", "yes")

    result = reply_to_latest_mention_replying(dry_run=dry)
    status = 200 if bool(result and result.get("ok")) else 500
    return jsonify(result), status




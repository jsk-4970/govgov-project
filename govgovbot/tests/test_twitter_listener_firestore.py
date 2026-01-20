import copy
from typing import Any, Dict, Optional

import pytest

from src.phase2 import twitter_listener
from src.phase2 import twitter_poster


class FakeDocSnapshot:
    def __init__(self, data: Optional[Dict[str, Any]]) -> None:
        self._data = copy.deepcopy(data) if data is not None else None

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Dict[str, Any]:
        if self._data is None:
            raise RuntimeError("Document does not exist")
        return copy.deepcopy(self._data)


class FakeDocRef:
    def __init__(self, store: Dict[str, Dict[str, Any]], doc_id: str) -> None:
        self._store = store
        self._doc_id = doc_id

    def get(self) -> FakeDocSnapshot:
        return FakeDocSnapshot(self._store.get(self._doc_id))

    def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        if merge and self._doc_id in self._store:
            self._store[self._doc_id].update(copy.deepcopy(data))
        else:
            self._store[self._doc_id] = copy.deepcopy(data)


class FakeCollection:
    def __init__(self) -> None:
        self.docs: Dict[str, Dict[str, Any]] = {}

    def document(self, doc_id: str) -> FakeDocRef:
        return FakeDocRef(self.docs, doc_id)


@pytest.fixture()
def fake_collection(monkeypatch: pytest.MonkeyPatch) -> FakeCollection:
    coll = FakeCollection()
    monkeypatch.setattr(twitter_listener, "_get_mentions_collection", lambda: coll)
    monkeypatch.setattr(twitter_listener.firestore, "SERVER_TIMESTAMP", "SERVER_TIMESTAMP", raising=False)
    return coll


def test_mark_and_check_firestore(fake_collection: FakeCollection) -> None:
    tid = "123"
    assert twitter_listener._is_replied_in_firestore(tid) is False

    twitter_listener._mark_replied_in_firestore(
        tid,
        reply_tweet_id="456",
        metadata={"mode": "reply", "note": "test"},
    )

    assert twitter_listener._is_replied_in_firestore(tid) is True
    stored = fake_collection.docs[tid]
    assert stored["replied"] is True
    assert stored["reply_tweet_id"] == "456"
    assert stored["mode"] == "reply"
    assert stored["note"] == "test"
    assert stored["updated_at"] == "SERVER_TIMESTAMP"


def test_reply_to_new_mentions_batch_marks_firestore(monkeypatch: pytest.MonkeyPatch, fake_collection: FakeCollection) -> None:
    mentions = [
        {"id": "101", "author_username": "alice"},
        {"id": "102", "author_username": "bob"},
    ]
    monkeypatch.setattr(twitter_listener, "poll_mentions", lambda limit=100, since_id=None: mentions)
    monkeypatch.setattr(twitter_listener, "_get_me_identity", lambda: ("me_id", "bot"))
    monkeypatch.setattr(twitter_listener, "fetch_conversation_latest", lambda tid: {"id": tid, "author_id": "other"})
    monkeypatch.setattr(twitter_listener, "fetch_conversation_text", lambda tid: f"text-{tid}")
    monkeypatch.setattr(twitter_listener, "build_rag_reply", lambda text: f"reply:{text}")

    posted: list[Dict[str, Any]] = []

    def fake_post_tweet(text: str, in_reply_to_tweet_id: Optional[str] = None, skip_throttle: bool = False) -> Dict[str, Any]:
        posted.append(
            {"text": text, "reply_to": in_reply_to_tweet_id, "skip_throttle": skip_throttle}
        )
        return {"id": f"r{in_reply_to_tweet_id or len(posted)}"}

    monkeypatch.setattr(twitter_poster, "post_tweet", fake_post_tweet)

    result = twitter_listener.reply_to_new_mentions_batch(dry_run=False, max_fetch=10)

    assert result["ok"] is True
    assert result["processed"] == 2
    assert result["fallback_posted"] == 0
    assert result["failed_fallback"] == 0
    assert posted == [
        {"text": "reply:text-101", "reply_to": "101", "skip_throttle": True},
        {"text": "reply:text-102", "reply_to": "102", "skip_throttle": True},
    ]
    for mention in mentions:
        doc = fake_collection.docs[mention["id"]]
        assert doc["replied"] is True
        assert doc["reply_tweet_id"] == f"r{mention['id']}"
        assert doc["mode"] == "reply"

    # 再実行時はFirestoreのフラグにより未処理項目がなくなる
    result_again = twitter_listener.reply_to_new_mentions_batch(dry_run=False, max_fetch=10)
    assert result_again["ok"] is True
    assert result_again["processed"] == 0
    assert result_again["reason"] == "all_already_replied"

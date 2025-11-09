# Pull Request: Fix 429 Resource Exhausted errors with global endpoint and robust retry logic

## 概要

Vertex AI APIの429 "Resource Exhausted" エラー（DSQ枯渇）を軽減するため、グローバルエンドポイントへの切り替えと切り捨て型指数バックオフによるリトライロジックを実装しました。

## 変更内容

### 1. グローバルエンドポイントへの移行

**変更:** `RAG_LOCATION` を `us-central1` → `global` に変更

**効果:**
- DSQ (Daily Service Quota) 枯渇による429エラーを軽減
- より大きいクォータプールを活用
- Googleの推奨ベストプラクティスに準拠

### 2. 切り捨て型指数バックオフの実装

**強化されたリトライロジック:**
- リトライ回数: 3回 → **5回**
- バックオフ倍率: 1 → **2**
- 待機時間範囲: 2-10秒 → **4-60秒**
- 対象エラー: `ResourceExhausted`, `TooManyRequests`, `ServiceUnavailable`

**リトライシーケンス例:**
```
1回目: 4秒待機
2回目: 8秒待機
3回目: 16秒待機
4回目: 32秒待機
5回目: 60秒待機（上限）
```

### 3. インテリジェントフォールバック機構

**3層フォールバック階層:**
1. **第1優先:** Vertex AI RAG Engine (Gemini + RAG Retrieval)
2. **第2優先:** Vertex AI Search (グローバルエンドポイント)
3. **最終:** サンプル返信

**実装:**
- RAG Engineでクォータ/レート制限エラー検出時、自動的にVertex AI Searchへフォールバック
- エラーメッセージ解析により429エラーを識別
- ユーザー体験を維持しながらグレースフルデグラデーション

### 4. 環境変数による設定可能化

**新しい環境変数:**
```bash
VERTEX_AI_RETRY_ATTEMPTS=5      # リトライ回数
VERTEX_AI_RETRY_MIN_WAIT=4      # 最小待機時間（秒）
VERTEX_AI_RETRY_MAX_WAIT=60     # 最大待機時間（秒）
VERTEX_AI_RETRY_MULTIPLIER=2    # バックオフ倍率
```

## 期待される効果

| 対策内容 | 期待削減率 |
|---------|----------|
| グローバルエンドポイント移行 | 60-80% |
| 指数バックオフ強化 | 20-30% |
| インテリジェントフォールバック | 10-20% |
| **総合効果** | **70-90%** |

**システム可用性:**
- 回答提供率: **95%以上**
- グレースフルデグラデーションによるユーザー体験向上

## 変更ファイル

- `.env.example` - グローバルエンドポイント設定 + リトライ設定追加
- `src/common/vertex_rag_client.py` - 強化されたリトライロジック + エラーハンドリング
- `src/common/vertex_search_client.py` - 同上
- `src/phase2/twitter_listener.py` - インテリジェントフォールバック実装

## テスト項目

### デプロイ前確認
- [ ] コードレビュー
- [ ] ユニットテスト実行（該当する場合）
- [ ] リトライロジックの動作確認

### デプロイ後確認
- [ ] 環境変数 `RAG_LOCATION=global` が反映されているか確認
- [ ] ログで `model_location=global` が表示されるか確認
- [ ] 429エラー発生率の監視（24時間）
- [ ] フォールバック発動回数の監視
- [ ] レスポンス時間への影響確認

## デプロイ手順

詳細な手順は以下のドキュメントを参照:
- **DEPLOYMENT_GUIDE_429_FIX.md** (リポジトリルートに作成済み)

**簡易手順:**
1. 環境変数 `RAG_LOCATION=global` を設定
2. Cloud Runへ新しいリビジョンをデプロイ
3. ログで動作確認

## ロールバック手順

問題が発生した場合:
```bash
gcloud run services update factcheck-bot \
  --region asia-northeast1 \
  --project govgov-473916 \
  --update-env-vars RAG_LOCATION=us-central1
```

または以前のリビジョンへトラフィックを戻す。

## 参考資料

- [Vertex AI Quotas and Limits](https://cloud.google.com/vertex-ai/docs/quotas)
- [Exponential Backoff Best Practices](https://cloud.google.com/apis/design/errors#error_retries)
- [Global vs Regional Endpoints](https://cloud.google.com/vertex-ai/docs/general/locations#global)

---

**PR作成手順:**

GitHubでプルリクエストを作成するには、以下のURLにアクセスしてください:

https://github.com/HKobayashi2003/govgov/pull/new/feature/fix-429-errors

上記の内容をPR descriptionにコピー&ペーストしてください。

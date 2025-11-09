# Changelog

## 2025-11-08 - 回答表示問題の修正

### 問題
ユーザーが質問を送信しても回答が表示されない問題が発生していました。

### 原因
1. **Vertex AI 安全フィルターによるブロック**: Vertex AI の Gemini モデルが政府予算に関する回答を誤って unsafe と判定し、ブロックしていた
2. **不十分な例外処理**: `response.text` にアクセス時に `ValueError` が発生し、適切に処理されていなかった
3. **フロントエンドのタイムアウト未実装**: バックエンドから応答がない場合、無限にローディング状態が続いていた

### 修正内容

#### バックエンド ([govgovbot/](govgovbot/))

1. **安全フィルター設定の追加** ([vertex_rag_client.py:11](govgovbot/src/common/vertex_rag_client.py#L11))
   - `HarmCategory` と `HarmBlockThreshold` をインポート
   - 安全フィルターを `BLOCK_ONLY_HIGH` に設定して誤検知を削減
   - 対象カテゴリ: HATE_SPEECH, DANGEROUS_CONTENT, SEXUALLY_EXPLICIT, HARASSMENT

2. **例外処理の強化** ([vertex_rag_client.py:158-166](govgovbot/src/common/vertex_rag_client.py#L158-L166))
   - `response.text` アクセス時の try/catch を追加
   - `ValueError` と `AttributeError` を捕捉
   - ブロックされた場合は空文字列を返し、警告ログを出力

3. **ストリーミング時の例外処理** ([vertex_rag_client.py:274-282](govgovbot/src/common/vertex_rag_client.py#L274-L282))
   - チャンクごとの try/catch を追加
   - エラー時は continue して次のチャンクへ進む

4. **空回答の処理** ([twitter_listener.py:1232-1235](govgovbot/src/phase2/twitter_listener.py#L1232-L1235))
   - 空の回答を受け取った場合、適切なメッセージを返す
   - 「申し訳ございません。該当する情報が見つかりませんでした。別の表現でお試しください。」

#### フロントエンド ([govgovweb/webapp/](govgovweb/webapp/))

1. **タイムアウト処理の実装** ([page.tsx:140-189](govgovweb/webapp/app/page.tsx#L140-L189))
   - 60秒のタイムアウトを設定
   - チャンクが一つも届かない場合、タイムアウトメッセージを表示
   - タイマーの適切なクリーンアップ処理

### デプロイ

```bash
# バックエンド (govgov-bot)
gcloud run deploy govgov-bot \
  --source /Users/aburi/Desktop/govgov/govgovbot \
  --platform managed \
  --region asia-northeast1 \
  --memory 2Gi \
  --project govgov-473916
```

**デプロイURL**: https://govgov-bot-335117605715.asia-northeast1.run.app

### テスト結果

```bash
# ヘルスチェック
curl https://govgov-bot-335117605715.asia-northeast1.run.app/
# {"ok":true,"root":true}

# API テスト
curl -X POST https://govgov-bot-335117605715.asia-northeast1.run.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"こども家庭庁の予算について教えてください"}'
# data: ご連絡ありがとうございます。現在ベータ運用中です...
# data: [DONE]
```

### 影響範囲
- バックエンド: Vertex AI RAG Engine の呼び出し処理全体
- フロントエンド: チャット UI の応答処理

### 今後の改善案
1. より詳細なエラーロギングとモニタリング
2. リトライロジックの最適化
3. 安全フィルターブロック時の代替応答メカニズム
4. フロントエンドでのエラーメッセージの改善

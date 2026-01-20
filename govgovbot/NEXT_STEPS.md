# 次のステップガイド

**プロジェクトID**: `govgov-473916`
**最終更新**: 2025-10-07

---

## 📊 プロジェクトステータス概要

### Phase 1: コア機能開発（ローカル環境）
**ステータス: ✅ ほぼ完了（95%）**

| 機能ID | 機能名 | ステータス | 備考 |
|--------|--------|----------|------|
| F-01 | ナレッジソース構築 | ✅ 完了 | RAG Corpus構築済み |
| F-02 | 擬似インターフェース | ✅ 完了 | `fact_check_cli.py` 実装済み |
| F-03 | ファクトチェック実行 | ✅ 完了 | Vertex AI RAG Engine実装済み |

### Phase 2: Twitter連携とクラウドデプロイ
**ステータス: 🚧 準備完了（実装開始可能）**

| 機能ID | 機能名 | ステータス | 備考 |
|--------|--------|----------|------|
| F-04 | メンション監視 | ⏳ 未着手 | `twitter_listener.py` テンプレート有り |
| F-05 | 回答投稿 | ⏳ 未着手 | `twitter_poster.py` テンプレート有り |

---

## ✅ Phase 1 完了内容（詳細）

### 1. インフラ・環境構築（100% 完了）

#### GCP環境
- ✅ プロジェクト作成: `govgov-473916`
- ✅ 必要なAPI有効化
  - Vertex AI API
  - Cloud Storage API
  - Secret Manager API
  - Discovery Engine API
- ✅ Cloud Storageバケット作成: `govgov-473916-data`
- ✅ サービスアカウント作成: `factcheck-bot-sa@govgov-473916.iam.gserviceaccount.com`
- ✅ 認証設定完了（Application Default Credentials）

#### Vertex AI RAG Engine
- ✅ RAG Corpus作成: `projects/govgov-473916/locations/us-east4/ragCorpora/2305843009213693952`
- ✅ 行政事業レビューデータのインポート完了
  - データソース: 行政事業レビュー基本情報（1_2_basicinfo）
  - ファイル数: 2ファイル（JSONL形式）
  - データ総量: 約16.7MB
- ✅ Gemini 2.0 Flash統合: `gemini-2.0-flash-exp`

#### ローカル開発環境
- ✅ Python 3.13.3 環境
- ✅ 依存関係インストール（`requirements.txt`）
- ✅ gcloud CLI認証設定

### 2. コア機能実装（100% 完了）

#### F-01: ナレッジソース構築 ✅
**実装済みファイル:**
- `data/1_2_basicinfo/output_converted_part1.jsonl` (9.96MB)
- `data/1_2_basicinfo/output_converted_part2.jsonl` (6.76MB)

**完了した作業:**
- 行政事業レビューCSVデータの取得
- JSONL形式への変換
- Cloud Storageへのアップロード
- Vertex AI RAG Corpusへのインポート

#### F-02: 擬似インターフェース（CLI） ✅
**実装ファイル:** `src/phase1/fact_check_cli.py`

**実装内容:**
- ✅ argparseによるコマンドライン引数解析
- ✅ 質問文の受け付け
- ✅ Vertex AI RAGクライアントとの統合
- ✅ フォーマットされた出力（判定、根拠、情報源、免責事項）
- ✅ エラーハンドリング
- ✅ ロギング

**動作確認コマンド:**
```bash
python3 src/phase1/fact_check_cli.py "JICAが移民を優遇してるって本当？"
```

#### F-03: ファクトチェック実行 ✅
**実装ファイル:** `src/common/vertex_rag_client.py`

**実装内容:**
- ✅ Vertex AI RAG Engine統合
  - `vertexai.generative_models.GenerativeModel`
  - `Tool.from_retrieval()` によるRAG設定
- ✅ RAG検索・回答生成機能
  - top_k設定（デフォルト: 5）
  - temperature設定（デフォルト: 0.7）
- ✅ グラウンディングメタデータ処理
  - 参照元の自動抽出
  - ソース情報のフォーマット
- ✅ 免責事項の自動付与
- ✅ リトライ処理（tenacity）
  - 3回リトライ
  - 指数関数的バックオフ
- ✅ 構造化ログ出力

### 3. ドキュメント整備（100% 完了）

- ✅ `README.md` - アーキテクチャとPhase 1完了を反映
- ✅ `docs/DEVELOPMENT.md` - チーム開発ガイド
- ✅ `docs/GCP_SETUP.md` - GCP環境構築ガイド
- ✅ `docs/GCP_SETUP_COMPLETE.md` - セットアップ完了レポート
- ✅ `docs/VERTEX_AI_SEARCH_SETUP.md` - Vertex AI関連セットアップ
- ✅ `docs/SEARCH_CLIENT_COMPARISON.md` - Search vs RAG Engine比較
- ✅ `docs/SECURITY.md` - セキュリティガイドライン
- ✅ `docs/GITHUB_COLLABORATION.md` - GitHub運用ルール
- ✅ `SETUP_STATUS.md` - セットアップ状況
- ✅ `CHANGES_2025_10_07.md` - 本日の変更履歴

### 4. 技術的成果

#### アーキテクチャ決定
- ✅ **Vertex AI RAG Engine採用** (Vertex AI Searchから移行)
  - より正確な回答生成
  - グラウンディング機能の活用
  - Gemini 2.0 Flashによる最新LLM活用

#### 課題解決
- ✅ **ライブラリ選択**: `google-generativeai` → `vertexai` へ移行
- ✅ **モデル互換性**: `gemini-2.0-flash-exp` が唯一利用可能と判明
- ✅ **リージョン最適化**:
  - RAG Corpus: `us-east4`
  - Gemini Model: `us-central1`
  - クロスリージョン構成で動作確認済み
- ✅ **エラーハンドリング**:
  - グラウンディングメタデータの正しい処理方法を確立
  - リトライロジックの実装

---

## 🎯 Phase 2: 次にやるべきこと

### 優先度: 最高 🔥

#### 1. Twitter API統合の実装

**目的**: SNS上での自動ファクトチェック機能の実現

**タスク詳細:**

##### F-04: メンション監視機能
**ファイル:** `src/phase2/twitter_listener.py`

**実装内容:**
- [ ] Twitter API v2認証設定
  - Bearer Token設定
  - OAuth 2.0認証フロー
- [ ] メンション取得機能
  - `/2/tweets/search/recent` エンドポイント使用
  - `@your_bot_name` を含むツイートの検索
- [ ] 新規メンションの検出
  - 最終チェック時刻の管理
  - 重複処理の防止
- [ ] メンション内容の抽出
  - 質問文の抽出
  - メンション送信者の情報取得

**推定工数**: 1-1.5日

##### F-05: 回答投稿機能
**ファイル:** `src/phase2/twitter_poster.py`

**実装内容:**
- [ ] `vertex_rag_client.py` の再利用
  - Phase 1で実装済みのRAGクライアントを流用
  - 追加の変更は不要
- [ ] ツイート投稿機能
  - `/2/tweets` エンドポイント使用
  - スレッド形式での返信
- [ ] 回答フォーマット調整
  - 280文字制限への対応
  - 複数ツイートへの分割ロジック
- [ ] レート制限対策
  - Twitter API制限の遵守
  - キューイング機構の実装

**推定工数**: 1-1.5日

##### 統合・動作確認
**ファイル:** `src/phase2/main.py`

**実装内容:**
- [ ] リスナーとポスターの統合
- [ ] エンドツーエンドテスト
  - 実際のTwitterアカウントでテスト
  - メンション→回答の一連のフロー確認
- [ ] エラーハンドリング強化

**推定工数**: 0.5日

**Phase 2合計推定工数**: 3日

---

#### 2. Cloud Runへのデプロイ

**目的**: 本番環境への展開とサーバーレス運用

**前提条件:**
- Phase 2 (F-04, F-05) の実装完了
- ローカルでのE2Eテスト完了

**タスク詳細:**

##### Dockerfile最適化
- [ ] マルチステージビルドの活用
- [ ] イメージサイズの最小化
- [ ] セキュリティスキャンの実施

##### Cloud Run設定
- [ ] サービスの作成
  - リージョン: `us-central1` (Geminiと同じ)
  - メモリ: 512MB（初期値）
  - CPU: 1（初期値）
- [ ] 環境変数の設定
  - Secret Managerとの連携
- [ ] サービスアカウントの割り当て
  - `factcheck-bot-sa` の使用

##### Secret Manager統合
- [ ] Twitter API認証情報の登録
  - `TWITTER_API_KEY`
  - `TWITTER_API_SECRET`
  - `TWITTER_ACCESS_TOKEN`
  - `TWITTER_ACCESS_TOKEN_SECRET`
  - `TWITTER_BEARER_TOKEN`
- [ ] アクセス権限の設定

##### CI/CDパイプライン構築
- [ ] GitHub Actionsワークフロー作成
  - `.github/workflows/deploy.yml`
- [ ] 自動テスト実行
- [ ] 自動デプロイ設定

**推定工数**: 1.5日

---

### 優先度: 高

#### 3. テストカバレッジの向上

**目的**: コード品質の保証とリファクタリングの安全性確保

**タスク:**
- [ ] `vertex_rag_client.py` のユニットテスト
  - モック化したVertex AI APIのテスト
  - エラーハンドリングのテスト
  - リトライロジックのテスト
- [ ] `fact_check_cli.py` の統合テスト
  - CLI引数解析のテスト
  - エンドツーエンドの動作テスト
- [ ] `twitter_listener.py` のユニットテスト
  - Twitter API呼び出しのモック化
  - メンション検出ロジックのテスト
- [ ] `twitter_poster.py` のユニットテスト
  - ツイート投稿のモック化
  - フォーマット処理のテスト

**カバレッジ目標:**
- `src/common/`: 85%以上
- `src/phase1/`: 70%以上
- `src/phase2/`: 70%以上

**推定工数**: 1.5日

---

#### 4. Cloud Loggingとモニタリング

**目的**: 本番運用時の監視体制の構築

**タスク:**
- [ ] Cloud Loggingの設定
  - 構造化ログの最適化
  - ログレベルの調整（本番: INFO以上）
- [ ] エラー通知の設定
  - Cloud Monitoringアラート
  - Slackへの通知統合（オプション）
- [ ] ダッシュボードの作成
  - リクエスト数
  - レスポンスタイム
  - エラー率

**推定工数**: 0.5日

---

### 優先度: 中（将来的な改善）

#### 5. パフォーマンス最適化

**タスク:**
- [ ] RAG検索パラメータのチューニング
  - `top_k` の最適値探索
  - `temperature` の調整
- [ ] レスポンスタイムの計測
  - Vertex AI API呼び出し時間
  - 回答生成時間
- [ ] キャッシュ戦略の検討
  - よくある質問のキャッシュ
  - Redis統合（オプション）

**推定工数**: 1日

---

#### 6. ナレッジソースの拡大

**タスク:**
- [ ] 追加データソースの検討
  - e-Govデータ
  - 国会議事録
  - 各省庁の報道発表資料
- [ ] データ収集スクリプトの拡張
- [ ] 定期的なデータ更新の自動化

**推定工数**: 2-3日（データソースによる）

---

#### 7. 回答品質の向上

**タスク:**
- [ ] プロンプトエンジニアリング
  - システムプロンプトの改善
  - Few-shot学習の導入
- [ ] 回答精度の評価
  - テストセットの作成
  - 人間による評価
- [ ] A/Bテスト
  - 複数の回答フォーマットの比較

**推定工数**: 2日

---

## 📅 推奨される開発スケジュール

### Week 1: Phase 2コア実装
- Day 1-2: F-04（メンション監視）実装
- Day 3-4: F-05（回答投稿）実装
- Day 5: 統合・E2Eテスト

### Week 2: デプロイ・テスト・改善
- Day 1-2: Cloud Runデプロイ
- Day 3: テストカバレッジ向上
- Day 4: モニタリング設定
- Day 5: 動作確認・ドキュメント更新

---

## 🔧 技術的な留意事項

### Vertex AI RAG Engine使用時の注意点

1. **リージョン制約**
   - RAG Corpus: `us-east4`（変更不可）
   - Gemini Model: `us-central1`で実行（必須）
   - クロスリージョン構成だが正常動作確認済み

2. **利用可能モデル**
   - ✅ `gemini-2.0-flash-exp` (現在使用中)
   - ❌ `gemini-1.5-pro`, `gemini-1.5-flash` (プロジェクトで利用不可)

3. **廃止予定機能**
   - `vertexai.generative_models` は2026年6月24日に廃止予定
   - 新しいSDKへの移行を将来検討する必要あり

### Twitter API制限

- **ツイート作成**: 300リクエスト/3時間
- **検索**: 180リクエスト/15分（Basic）
- **レスポンス**: 280文字制限（長文は分割必要）

### Cloud Run制約

- **リクエストタイムアウト**: 最大60分（デフォルト: 5分）
- **同時実行**: デフォルト80（調整可能）
- **コールドスタート**: 初回レスポンスが遅い可能性

---

## 💡 よくある問題と解決策

### Q1: モデルが404エラーで見つからない

```python
# ❌ 間違い
model_name = "gemini-1.5-pro-002"

# ✅ 正しい
model_name = "gemini-2.0-flash-exp"
```

### Q2: グラウンディングメタデータが取得できない

```python
# retrieval_metadataは単一オブジェクトの場合がある
if hasattr(grounding_metadata, 'retrieval_metadata'):
    retrieval_metadata = grounding_metadata.retrieval_metadata
    if isinstance(retrieval_metadata, list):
        # リストの場合
        for retrieval in retrieval_metadata:
            process(retrieval)
    else:
        # 単一オブジェクトの場合
        process(retrieval_metadata)
```

### Q3: Twitter APIのレート制限エラー

```python
# tenacityでリトライ + レート制限対応
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=60, max=300),
    retry=retry_if_exception_type(TooManyRequests)
)
def post_tweet(content):
    ...
```

---

## 📚 参考ドキュメント

### プロジェクト内
- [README.md](README.md) - プロジェクト概要
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - 開発フロー
- [docs/GCP_SETUP.md](docs/GCP_SETUP.md) - GCP環境構築
- [docs/VERTEX_AI_SEARCH_SETUP.md](docs/VERTEX_AI_SEARCH_SETUP.md) - Vertex AI詳細
- [docs/SECURITY.md](docs/SECURITY.md) - セキュリティガイドライン
- [SETUP_STATUS.md](SETUP_STATUS.md) - セットアップ状況
- [CHANGES_2025_10_07.md](CHANGES_2025_10_07.md) - 本日の変更履歴

### 外部リソース
- [Vertex AI RAG Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview)
- [Twitter API v2](https://developer.x.com/en/docs/twitter-api)
- [Cloud Run](https://cloud.google.com/run/docs)
- [GitHub Actions](https://docs.github.com/en/actions)

---

## 🎯 今すぐやるべきこと

### Phase 2実装を開始するには:

1. **Twitter API認証情報の取得**
   - [Twitter Developer Portal](https://developer.x.com/)でアプリ作成
   - API KeysとTokensを取得
   - `.env`に設定

2. **F-04実装開始**
   ```bash
   git checkout -b feature/F-04-twitter-listener
   # src/phase2/twitter_listener.py の実装開始
   ```

3. **動作確認**
   ```bash
   # テスト実行
   python -m src.phase2.twitter_listener
   ```

---

**Phase 1は完了しました！Phase 2に進みましょう 🚀**

**最終更新**: 2025-10-07
**更新者**: Claude (AI Assistant)

# govgov - 行政事業レビューファクトチェックBot

行政事業レビューデータを活用した、SNS上の偽・誤情報に対抗するファクトチェックBotのプロトタイプ

## 📋 プロジェクト概要

このプロジェクトは、政府が公開する「行政事業レビュー」データを活用し、SNS上で流通する根拠不明の情報に対して、信頼性の高い一次情報を提供するBotシステムです。Vertex AI RAG（Retrieval-Augmented Generation）技術で根拠を検索・要約し、X（Twitter）上のメンションに自動返信します。

## ✅ 動作確認済み（2025-10-09）

```bash
python3 src/phase1/fact_check_cli.py "デジタル庁の予算について教えてください"
python3 src/phase1/fact_check_cli.py "防衛省の予算について教えてください"
```

RAG検索とGemini回答生成が正常に動作しています。

### 社会的意義

- 偽・誤情報の拡散を抑制
- 政府の信頼できる一次情報へのアクセスを容易化
- 事実に基づいた建設的な議論の促進

## 🏗️ アーキテクチャ

- **コア技術**: Vertex AI RAG Engine (Retrieval-Augmented Generation)
- **LLMモデル**: Gemini 2.0 Flash (Experimental)
- **実行環境**: Google Cloud Run (サーバーレス)
- **連携サービス**: Twitter API, Secret Manager
- **言語**: Python 3.11+

## 📂 プロジェクト構造

```
govgov/
├── src/
│   ├── phase1/          # フェーズ1: コア機能開発
│   │   ├── knowledge_source.py    # F-01: ナレッジソース構築
│   │   ├── factcheck.py           # F-03: ファクトチェック実行
│   │   └── cli.py                 # F-02: 擬似インターフェース
│   ├── phase2/          # フェーズ2: Twitter連携
│   │   ├── twitter_listener.py    # F-04: メンション監視
│   │   ├── twitter_poster.py      # F-05: 回答投稿
│   │   └── main.py                # Cloud Run エントリポイント
│   └── common/          # 共通ロジック
│       ├── estat_client.py        # e-Stat APIクライアント
│       ├── gcs_uploader.py        # GCSアップローダー
│       ├── secret_manager.py      # Secret Manager統合
│       ├── vertex_rag_client.py   # Vertex AI RAGクライアント
│       └── config.py              # 設定管理
├── data/
│   ├── estat/           # e-Stat ETLパイプライン
│   │   ├── main.py                # ETLメイン処理
│   │   └── requirements.txt       # ETL用依存関係
│   └── 1_2_basicinfo/   # 行政事業レビューデータ
├── config/              # 設定ファイル
├── tests/               # テストコード
├── requirements.txt     # Python依存関係
├── Dockerfile           # コンテナ定義
└── .env.example         # 環境変数テンプレート
```

## 🚀 開発フェーズ

### フェーズ1: コア機能開発（ローカル環境）

| 機能ID | 機能名 | 説明 | ステータス |
|--------|--------|------|----------|
| F-01 | ナレッジソース構築 | 行政事業レビューデータのVertex AI RAG Corpusへのインポート | ✅ 完了 |
| F-02 | 擬似インターフェース | CLI経由での質問入力・回答出力 | ✅ 完了 |
| F-03 | ファクトチェック実行 | Vertex AI RAG Engine + Gemini 2.0を使用した回答生成 | ✅ 完了 |

### フェーズ2: X 連携とクラウドデプロイ

| 機能ID | 機能名 | 説明 |
|--------|--------|------|
| F-04 | メンション監視 | X APIでのメンション/自社宛リプライの取得（安全なポーリング） |
| F-05 | 回答投稿 | 検索/RAGで回答を生成し、自動返信（失敗時は通常投稿にフォールバック） |

## 🛠️ セットアップ

### クイックスタート（チーム開発者向け）

詳細な手順は以下のドキュメントを参照してください:

- **[開発ガイド](docs/DEVELOPMENT.md)** - 開発環境のセットアップと開発フロー
- **[GCPセットアップガイド](docs/GCP_SETUP.md)** - Google Cloud Platform環境の構築手順

### 前提条件

- Python 3.10以上
- Google Cloud アカウント
- Docker Desktop
- Google Cloud SDK (gcloud CLI)

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd govgov
```

### 2. 仮想環境の構築

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化 (Mac/Linux)
source venv/bin/activate

# 仮想環境を有効化 (Windows)
.\venv\Scripts\activate
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. Google Cloud環境のセットアップ

**初めての方**: [GCPセットアップガイド](docs/GCP_SETUP.md) に従って、GCP環境を構築してください。

**既にセットアップ済みの方**:

```bash
# gcloudにログイン
gcloud auth login

# アプリケーションのデフォルト認証情報の設定
gcloud auth application-default login

# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID
```

### 5. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集して、必要な値を設定
```

**必須の環境変数**:

```bash
# Google Cloud Platform
PROJECT_ID=govgov-473916

# Vertex AI RAG Engine
RAG_CORPUS_RESOURCE_NAME=projects/govgov-473916/locations/us-east4/ragCorpora/2305843009213693952
RAG_LOCATION=us-central1
MODEL_NAME=gemini-2.0-flash-exp

# X (Twitter) API - OAuth1.0a（Bot投稿に使用）
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...

# 画面名（@は不要）
X_BOT_SCREEN_NAME=govgovjapan

# 必須: アプリ専用ベアラートークン（メンション取得に必須）
# 注意: Bearer Tokenがないとメンション取得が失敗します（Free/Basicプランでも動作する方法）
# 詳細は docs/X_API_AUTHENTICATION.md を参照
X_BEARER_TOKEN=...

# 任意: 長文ツイートの上限（Premiumに合わせて調整）
X_MAX_TWEET_LEN=10000

# 任意: 投稿スロットル（レート制御）
POST_MIN_INTERVAL_SEC=60
POST_MAX_PER_MINUTE=8
POST_MAX_PER_HOUR=200

# 任意: メンションポーリング間隔（秒）
MENTION_POLL_INTERVAL_SEC=90
```

詳細は [GCPセットアップガイド](docs/GCP_SETUP.md) を参照してください。

## 🎯 使い方

### フェーズ1: ローカルでのファクトチェック実行

```bash
# ファクトチェックCLIツールを実行
python src/phase1/fact_check_cli.py "JICAが移民を優遇してるって本当？"

# または、別の質問で実行
python src/phase1/fact_check_cli.py "デジタル庁の予算について教えてください"
```

### フェーズ2: 連携の使い方（ローカル）

検索/RAGとX投稿の統合が完了しています。以下はよく使う実行例です。

```bash
# 最新メンションへ返信（失敗時は通常投稿にフォールバック）
python -c "from src.phase2.twitter_listener import reply_to_latest_mention_replying; import json; print(json.dumps(reply_to_latest_mention_replying(dry_run=False), ensure_ascii=False))"

# 自社ポストに付いた最新リプライに返信（失敗時は通常投稿）
python -c "from src.phase2.twitter_listener import reply_to_latest_replier_replying; import json; print(json.dumps(reply_to_latest_replier_replying(dry_run=False), ensure_ascii=False))"

# メンションをポーリング（表示のみ。運用時は60–120秒推奨）
python -c "from src.phase2.twitter_listener import run_loop; run_loop()"
```

生成される本文は以下の仕様です。
- Markdownの `**` や `*` を除去し、文末（。!?）単位で適度に改行
- 本文末尾に「出典: URL …」を可能な範囲で付与
- Premiumに合わせ長文に対応（`X_MAX_TWEET_LEN` 既定 10000）

### フェーズ2: Cloud Runへのデプロイ

```bash
# Dockerイメージのビルド
docker build -t factcheck-bot .

# Cloud Runへのデプロイ
gcloud run deploy factcheck-bot \
  --image factcheck-bot \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

## 🧪 テスト

```bash
# 全テストの実行
pytest

# カバレッジ付きでテスト実行
pytest --cov=src tests/
```

## 📝 回答フォーマット

Botが生成する回答には以下の要素が含まれます:

- ✅/❌ 判定ラベル
- 根拠の要約
- 情報源URL（本文末尾に付与）
- 免責事項（AIによる参考情報である旨）

## ⚠️ 注意事項

- このBotは100%の正確性を保証するものではありません
- 生成される情報はあくまでAIによる参考情報です
- レート制御の目安（Per User / Per App）
  - GET /2/users/:id/mentions … 10 / 15分
  - GET /2/tweets/search/recent … 60 / 15分
  - GET /2/users/:id/timelines/reverse_chronological … 5 / 15分
  - 本リポジトリでは `POST_*` と `MENTION_POLL_INTERVAL_SEC` で安全側にスロットリングしています

- プロトタイプ段階のため、本番運用には追加の検証が必要です

## 📚 ドキュメント

### プロジェクト内ドキュメント

- **[開発ガイド](docs/DEVELOPMENT.md)** - チーム開発のための開発環境セットアップと開発フロー
- **[GCPセットアップガイド](docs/GCP_SETUP.md)** - Google Cloud Platform環境の詳細な構築手順
- **[セキュリティガイドライン](docs/SECURITY.md)** - 機密情報管理とセキュリティベストプラクティス（必読）
- **[GitHubコラボレーションガイド](docs/GITHUB_COLLABORATION.md)** - チーム開発のワークフローとルール
- **[X API認証ガイド](docs/X_API_AUTHENTICATION.md)** - X API認証の詳細と重要な知見（Bearer Token必須）

### 参考資料

- [要件定義書](../txt/rd.txt) - プロジェクトの詳細な要件と仕様
- [環境セットアップガイド（参考）](../txt/envsetup1.txt) - 初期セットアップの参考資料
- [Vertex AI Search ドキュメント](https://cloud.google.com/generative-ai-app-builder/docs) - Google公式ドキュメント
- [行政事業レビュー公式サイト](https://www.gyoukaku.go.jp/) - データソース

## 🔧 e-Stat API ETLパイプライン

政府統計の総合窓口（e-Stat）から統計データを自動取得し、GCSに保存するETLパイプラインが実装されています。

### 主な機能

- e-Stat APIから全統計表データを自動取得（ページネーション対応）
- JSONL形式でGCSに保存（日付ごとのフォルダに整理）
- Secret Managerによる認証情報の安全な管理
- リトライ処理とエラーハンドリング
- Cloud Functions/Cloud Runでの定期実行対応

### 実行方法

```bash
# ローカル実行（テスト: 最初の10件のみ）
cd data/estat
export PROJECT_ID=govgov-473916
export BUCKET_NAME=govgov-473916-estat-data
export MAX_STATS_COUNT=10
python main.py

# Cloud Functionsへのデプロイ
gcloud functions deploy estat-etl \
  --gen2 \
  --runtime=python311 \
  --region=asia-northeast1 \
  --source=./data/estat \
  --entry-point=cloud_function_entry \
  --trigger-http \
  --service-account=estat-etl@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=${PROJECT_ID},BUCKET_NAME=${BUCKET_NAME}
```

詳細は [data/estat/README.md](data/estat/README.md) を参照してください。

## 🔮 将来展望

- ナレッジソースの拡大（e-Stat統計データ、e-Gov、国会議事録など）
- CI/CDパイプラインの構築
- 本番運用に向けた監視体制の整備
- マルチステークホルダー・プロセスへの発展
- AI SEO対応

## 📄 ライセンス

TBD

## 🤝 コントリビューション

プロトタイプ開発段階のため、コントリビューションガイドラインは準備中です。

---

**開発ステータス**: プロトタイプ開発中（フェーズ1）

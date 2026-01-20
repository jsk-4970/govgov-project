# GovGovWeb

政府情報ファクトチェックWebアプリケーション

## 概要

このリポジトリは、行政事業レビューデータや法律データに基づいて政府情報のファクトチェックを行うWebアプリケーションです。

Vertex AI RAGを利用して、ユーザーからの質問に対して信頼性の高い回答を提供します。

## 主な機能

- ユーザーフレンドリーなWebインターフェース（Next.js + TypeScript）
- Vertex AI RAGによる高精度な回答生成
- 参照元情報の明示
- 免責事項の自動付与

## 技術スタック

- **フロントエンド**: Next.js 14, TypeScript, Tailwind CSS
- **バックエンドAPI**: Next.js API Routes
- **AI/ML**: Google Cloud Vertex AI RAG
- **デプロイ**: Google Cloud Run
- **コンテナ**: Docker

## リポジトリ構成

```
GovGovWeb/
├── webapp/                 # Next.jsアプリケーション
│   ├── app/               # App Router
│   │   ├── api/          # API Routes
│   │   └── page.tsx      # メインページ
│   ├── Dockerfile        # Webアプリ用コンテナ設定
│   └── deploy-cloudrun.sh # デプロイスクリプト
├── src/                   # バックエンドロジック
│   └── common/           # 共通モジュール
│       ├── vertex_rag_client.py  # RAGクライアント
│       ├── factcheck_prompt.py   # プロンプト生成
│       └── disclaimer.py         # 免責事項
└── docs/                  # ドキュメント
```

## セットアップ

### 前提条件

- Node.js 18以上
- Python 3.11以上
- Google Cloud CLIのインストールと認証
- GCPプロジェクトの作成とVertex AI APIの有効化

### ローカル開発

1. リポジトリをクローン

```bash
git clone git@github.com:jsk-4970/GovGovWeb.git
cd GovGovWeb
```

2. 環境変数の設定

```bash
cd webapp
cp .env.local.example .env.local
# .env.localを編集してGCP設定を記入
```

3. 依存関係のインストール

```bash
npm install
```

4. 開発サーバーの起動

```bash
npm run dev
```

http://localhost:3000 でアクセス可能

### 本番デプロイ

詳細は [DEPLOYMENT.md](DEPLOYMENT.md) および [QUICKSTART_PRODUCTION.md](QUICKSTART_PRODUCTION.md) を参照してください。

```bash
cd webapp
./deploy-cloudrun.sh
```

## デプロイ済みサービス

現在、以下のURLで本番環境が稼働しています:

- **Webアプリケーション**: https://govgovweb-67tdojz6sq-an.a.run.app
- **バックエンドAPI**: https://factcheck-bot-67tdojz6sq-an.a.run.app

## 開発ガイドライン

本プロジェクトの開発規約は [CLAUDE.md](CLAUDE.md) に記載されています。

主要ポイント:
- PEP8準拠のPythonコーディングスタイル
- 型ヒントの必須使用
- Googleスタイルのdocstring
- 免責事項の必須付与
- Conventional Commitsによるコミットメッセージ

## 関連リポジトリ

- [govgov](https://github.com/HKobayashi2003/govgov) - Twitter Bot版（メインリポジトリ）

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueで議論してください。
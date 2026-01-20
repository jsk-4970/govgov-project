# GovGovWeb - Web Application

行政事業レビューデータに基づいたAIファクトチェックサービスのWebアプリケーション

## 概要

このWebアプリケーションは、ユーザーが行政事業に関する質問を入力すると、AIがリアルタイムで回答をストリーミング表示する、ChatGPTのようなUIを持つシングルページアプリケーションです。

## 技術スタック

- **フレームワーク**: Next.js 14 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS
- **AI統合**: Vercel AI SDK
- **デザイン参考**: みらい議会 (gikai.team-mir.ai)

## 主要機能

### 1. ストリーミングAPI (`/api/ask`)
- Next.jsのAPI Routeとして実装
- POSTリクエストで `{ "question": "ユーザーの質問文" }` を受け取る
- **現在はモック実装**: ダミーテキストを1文字ずつストリーミングで返す
- Vercel AI SDKの `StreamingTextResponse` を使用

### 2. チャットUI (`app/page.tsx`)
- **チャット表示エリア**: 会話履歴をスクロール可能に表示
- **入力フォームエリア**: 画面下部に固定、テキスト入力と送信ボタン
- **レスポンシブデザイン**: モバイル・デスクトップ両対応
- **リアルタイムストリーミング**: Vercel AI SDKの `useChat` フックで実装

### 3. デザイン
- クリーンでミニマルなUI
- ダークモード対応
- スムーズなアニメーション
- アクセシビリティ考慮

## セットアップ

### 前提条件
- Node.js 18.x 以上
- npm または yarn

### インストール手順

```bash
# webappディレクトリに移動
cd webapp

# 依存関係のインストール
npm install

# 開発サーバーの起動
npm run dev
```

開発サーバーが起動したら、ブラウザで [http://localhost:3000](http://localhost:3000) を開いてください。

### ビルドとデプロイ

```bash
# プロダクションビルド
npm run build

# プロダクションサーバーの起動
npm start
```

## デプロイ

このWebアプリケーションは、Vercel または Google Cloud Run にデプロイできます。

### オプション1: Vercel にデプロイ（推奨）

Next.jsアプリケーションに最適化されたVercelへのデプロイが推奨です。

#### Vercel CLI を使用

```bash
# Vercelにログイン（初回のみ）
npx vercel login

# デプロイ（プレビュー環境）
npx vercel

# 本番環境にデプロイ
npx vercel --prod
```

#### Vercel ダッシュボードを使用

1. [Vercel](https://vercel.com) にアクセスしてログイン
2. 「New Project」をクリック
3. GitHubリポジトリ `HKobayashi2003/govgov` を選択
4. **Root Directory** を `webapp` に設定
5. **Framework Preset** が `Next.js` になっていることを確認
6. 「Deploy」をクリック

### オプション2: Google Cloud Run にデプロイ

GCP環境を活用する場合は、Cloud Runにデプロイできます。

```bash
# webappディレクトリに移動
cd webapp

# デプロイスクリプトを実行
./deploy-cloudrun.sh
```

または手動でデプロイ:

```bash
# Dockerイメージをビルド
docker build -t gcr.io/govgov-473916/govgovweb .

# イメージをプッシュ
docker push gcr.io/govgov-473916/govgovweb

# Cloud Runにデプロイ
gcloud run deploy govgovweb \
  --image gcr.io/govgov-473916/govgovweb \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --port 3000
```

## ディレクトリ構造

```
webapp/
├── app/                    # Next.js App Router
│   ├── api/               # APIルート
│   │   └── ask/
│   │       └── route.ts   # ストリーミングAPI
│   ├── layout.tsx         # ルートレイアウト
│   ├── page.tsx           # メインチャットUI
│   └── globals.css        # Tailwind CSS
├── public/                # 静的ファイル
├── package.json           # Node依存関係
├── tsconfig.json          # TypeScript設定
├── tailwind.config.ts     # Tailwind設定
├── postcss.config.js      # PostCSS設定
├── next.config.js         # Next.js設定
└── .gitignore            # Git除外設定
```

## 開発ガイド

### APIエンドポイントのカスタマイズ

現在の `/api/ask` はモック実装です。実際のバックエンドロジック（Vertex AI Search連携など）に置き換える場合は、[app/api/ask/route.ts](app/api/ask/route.ts) を編集してください。

```typescript
// 例: 実際のVertex AI Search呼び出し
import { VertexAISearchClient } from '@/lib/vertex-search';

export async function POST(req: Request) {
  const { question } = await req.json();

  // Vertex AI Searchを呼び出し
  const client = new VertexAISearchClient();
  const results = await client.search(question);

  // ストリーミングレスポンスを返す
  // ...
}
```

### UIのカスタマイズ

UIコンポーネントは [app/page.tsx](app/page.tsx) にあります。Tailwind CSSのユーティリティクラスを使ってスタイリングしています。

色やレイアウトを変更する場合は、直接このファイルを編集するか、[tailwind.config.ts](tailwind.config.ts) でテーマをカスタマイズしてください。

## トラブルシューティング

### ポート3000が既に使用されている場合

```bash
# 別のポートで起動
PORT=3001 npm run dev
```

### 依存関係のエラー

```bash
# node_modulesを削除して再インストール
rm -rf node_modules package-lock.json
npm install
```

### TypeScriptのエラー

```bash
# 型チェックを実行
npx tsc --noEmit
```

## 次のステップ

1. **バックエンド統合**: モックAPIを実際のVertex AI Search APIに置き換え
2. **認証機能**: ユーザーログイン機能の追加
3. **会話履歴**: チャット履歴の保存と読み込み機能
4. **エラーハンドリング**: より詳細なエラーメッセージと再試行ロジック
5. **テスト**: Jest/React Testing Libraryでのテスト追加
6. **デプロイ**: Vercel/Cloud Runへのデプロイ設定

## ライセンス

このプロジェクトは非公開です。

## 参考資料

- [Next.js Documentation](https://nextjs.org/docs)
- [Vercel AI SDK](https://sdk.vercel.ai/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript](https://www.typescriptlang.org/docs)

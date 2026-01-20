# プロジェクト設計ルール

このドキュメントは、本プロジェクトにおける設計思想、コーディング規約、運用ルールを定めたものです。
LLMによるコード生成や、チームメンバーによる開発において、常にこのルールに従ってください。

---

## 1. ディレクトリ構造と責務

プロトタイプのフェーズ管理において分かりやすい構造を維持しつつ、コードの再利用性と将来の拡張性を担保します。

### 1.1 全体構造

**重要: GovGovWebとgovgovbotの関係性**

本プロジェクトは **GovGovWeb** (このリポジトリ) と **govgovbot** の2つのアプリケーションから構成されています:

```
govgov/ (リポジトリルート)
├── govgovbot/              # Twitter Bot アプリケーション
│   ├── src/
│   │   ├── phase1/        # フェーズ1（コア機能・ローカル検証用）
│   │   ├── phase2/        # フェーズ2（Twitter Bot + Web API）
│   │   │   ├── main.py           # Flask アプリケーション本体
│   │   │   ├── twitter_listener.py  # Bot応答ロジック + テキスト整形
│   │   │   └── twitter_poster.py    # Twitter投稿機能
│   │   └── common/        # Bot独自の共通ロジック
│   ├── main.py            # Cloud Functions エントリーポイント
│   └── CLAUDE.md          # Bot用設計ルール
│
└── GovGovWeb/              # Web UI アプリケーション (このリポジトリ)
    ├── webapp/            # Next.js アプリケーション
    │   ├── app/
    │   │   ├── api/ask/route.ts  # API Route (govgovbotのFlaskを呼び出す)
    │   │   └── page.tsx          # メインページUI
    │   └── Dockerfile
    ├── src/
    │   └── common/        # Web独自の共通ロジック（RAGクライアント等）
    └── CLAUDE.md          # このファイル（Web用設計ルール）
```

### 1.2 アーキテクチャの重要な違い

| 項目 | GovGovWeb (このリポジトリ) | govgovbot |
|------|-----------|-----------|
| **目的** | Webブラウザから利用可能なUI | Twitter Bot として動作 |
| **フロントエンド** | Next.js 14 + TypeScript | なし（Twitter がUI） |
| **バックエンドAPI** | Next.js API Routes → **govgovbotのFlaskを呼び出す** | Flask (Python) |
| **エンドポイント** | Next.js `/api/ask` → Flask `/api/ask` | `/tweet`, `/tasks/reply-latest`, `/tasks/reply-new-mentions`, **`/api/ask`** |
| **デプロイ先** | Google Cloud Run (Next.js) | Google Cloud Run (Flask) + Cloud Functions |
| **応答生成ロジック** | **govgovbotの関数を呼び出す** | `src/phase2/twitter_listener.py` の `build_rag_reply()` と `_compose_tweet_from_search_result()` |
| **テキスト整形** | **govgovbotの `_normalize()` 関数を使用** | `_normalize()` 関数で日本語テキストを整形 |

### 1.3 コードの共有と依存関係

**重要: バックエンドロジックはgovgovbotに依存**

- **GovGovWebはフロントエンド（UI）のみを提供**
- **バックエンドAPI（`/api/ask`）は govgovbot の Flask サーバーを呼び出す**
- テキスト整形、RAG呼び出し、回答生成は全て govgovbot 側で実施
- **GovGovWebではバックエンドロジックを実装しない**

**アーキテクチャフロー:**
```
ユーザー (ブラウザ)
    ↓
Next.js UI (GovGovWeb)
    ↓ POST /api/ask (Next.js API Route)
    ↓
govgovbot Flask Server
    ↓ build_rag_reply() in twitter_listener.py
    ↓ _compose_tweet_from_search_result()
    ↓ _normalize() でテキスト整形
    ↓
JSON レスポンス {"ok": true, "answer": "...", "sources": [...]}
    ↓
Next.js がストリーミング表示
    ↓
ユーザー (ブラウザ)
```

**コード修正時の注意:**
- ❌ **NG**: GovGovWebで独自のテキスト整形ロジックを実装
- ❌ **NG**: GovGovWebで独自のRAGクライアントを実装
- ✅ **OK**: 必要な変更は govgovbot 側で実施し、GovGovWebは API 呼び出しのみ
- ✅ **OK**: UI/UX の改善は GovGovWeb で実施

### 1.4 GovGovWeb ディレクトリ構造

```
GovGovWeb/
├── webapp/                 # Next.jsアプリケーション
│   ├── app/               # App Router
│   │   ├── api/          # API Routes
│   │   │   └── ask/
│   │   │       └── route.ts  # 【重要】govgovbot Flask APIを呼び出す
│   │   ├── page.tsx      # メインページ
│   │   └── layout.tsx    # レイアウト
│   ├── public/           # 静的ファイル
│   ├── Dockerfile        # Webアプリ用コンテナ設定
│   ├── package.json      # Node.js依存関係
│   └── deploy-cloudrun.sh # デプロイスクリプト
├── src/                   # バックエンドロジック（最小限）
│   └── common/           # 共通モジュール
│       ├── vertex_rag_client.py  # RAGクライアント（参考用、未使用の可能性あり）
│       ├── factcheck_prompt.py   # プロンプト生成（参考用）
│       └── disclaimer.py         # 免責事項（参考用）
└── docs/                  # ドキュメント
```

**重要原則:**
- **フロントエンド（Next.js）の開発に集中**
- バックエンドロジックは govgovbot に依存
- `src/common/` 内のファイルは参考用（実際の処理は govgovbot で実施）
- 環境変数 `BACKEND_API_URL` で govgovbot の Flask サーバーを指定

### 1.5 API連携の設定

**環境変数 (`.env.local`):**
```bash
# govgovbot Flask サーバーのURL
BACKEND_API_URL=http://localhost:8080  # ローカル開発
# または
BACKEND_API_URL=https://govgovbot-xxxxx.run.app  # 本番環境
```

**API呼び出し例 (`webapp/app/api/ask/route.ts`):**
```typescript
const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8080';
const apiUrl = `${backendUrl}/api/ask`;

const response = await fetch(apiUrl, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ question }),
});

const data = await response.json();
// { ok: true, answer: "...", sources: [...] }
```

---

## 2. コーディング規約

コードの一貫性は、メンテナンス性とチーム開発の効率を飛躍的に向上させます。

### 2.1 Pythonコーディングスタイル

**原則:** PEP8準拠

**自動化ツール:**
- `black`: コードフォーマッタ（行幅88文字）
- `isort`: import文の自動整理
- Gitフック（pre-commit）で自動実行を推奨

### 2.2 型ヒント

**要件:** 必須

全ての関数・メソッドの引数と戻り値に型ヒントを付けます。

```python
# Good
def search_documents(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """ドキュメントを検索する"""
    ...

# Bad
def search_documents(query, max_results=5):
    ...
```

**メリット:**
- 静的解析ツール（mypy）によるバグの早期発見
- IDEによる強力な入力補完
- コードの可読性向上

**検証:** `mypy` による型チェックをCI/CDに組み込む

### 2.3 docstringのスタイル

**推奨:** Googleスタイル

```python
def format_answer_with_disclaimer(answer: str, sources: list[str]) -> str:
    """回答に免責事項を付与する

    Args:
        answer: AIが生成した回答文
        sources: 参照元のURL・文書名のリスト

    Returns:
        免責事項が付与された回答文

    Raises:
        ValueError: answerが空文字列の場合
    """
    if not answer:
        raise ValueError("answer must not be empty")

    disclaimer = "※ この回答はAIによって生成されたものであり、100%の正確性を保証するものではありません。"
    return f"{answer}\n\n{disclaimer}\n\n参照元:\n" + "\n".join(sources)
```

---

## 3. GCP関連の設計ルール

クラウドサービスとの連携は本プロジェクトの要です。安定性とセキュリティを両立させます。

### 3.1 API呼び出しのエラーハンドリング

**リトライ処理:**
- ライブラリ: `tenacity` を使用
- 戦略: 指数関数的バックオフ（Exponential Backoff）
- 対象: Vertex AI、Twitter APIなど全ての外部サービス

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def call_vertex_ai_search(query: str) -> dict:
    """Vertex AI Searchを呼び出す（自動リトライ付き）"""
    ...
```

**カスタム例外:**
- 各APIクライアントごとに独自の例外クラスを定義
- 例: `VertexAISearchError`, `TwitterAPIError`

**タイムアウト設定:**
- 全てのAPI呼び出しに適切なタイムアウト値を設定
- 無限に待ち続けることを防ぐ

### 3.2 ログの出力

**フォーマット:** 構造化ログ（JSON形式）

Google Cloud Loggingが自動で解釈できる形式で出力します。

**必須フィールド:**
- `severity`: ログレベル（INFO, WARNING, ERROR等）
- `timestamp`: タイムスタンプ
- `message`: 処理内容
- `trace_id`: リクエストごとのトレースID（可能であれば）

**レベル基準:**
- `INFO`: 処理の開始・終了
- `WARNING`: リトライが発生した場合
- `ERROR`: 処理が失敗した場合
- `DEBUG`: 詳細なデバッグ情報（本番環境では無効化）

### 3.3 認証情報の管理

**原則:** Google Secret Manager を全面的に利用

**ローカル開発:**
- `gcloud auth application-default login` を実行
- Application Default Credentials (ADC) を利用
- ローカル環境とCloud Run環境でコードを変更しない

**厳禁事項:**
- コード内での認証情報の直接記述
- `.env` ファイルのGitコミット

---

## 4. GitHub運用ルール

スムーズな共同作業と品質管理のため、明確なワークフローを定義します。

### 4.1 ブランチ戦略

**採用:** GitHub Flow

1. `main` ブランチは常にデプロイ可能な状態を維持
2. 開発は `main` から切った `feature/issue-number-description` ブランチで実施
3. 開発完了後、`main` に対してプルリクエスト（PR）を作成
4. レビュー・CI通過後にマージ

### 4.2 プルリクエスト（PR）

**要件:** 必須

**PRテンプレートに含める項目:**
- 変更内容の概要
- 変更の目的・背景
- テスト方法
- スクリーンショット（UI変更の場合）

**マージ条件:**
- CIパス（自動テスト、リンター、型チェック）
- 最低1人以上のレビュー（セルフレビューも可）

### 4.3 コミットメッセージ

**形式:** Conventional Commits

**接頭辞:**
- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント
- `refactor:` リファクタリング
- `test:` テスト追加・修正
- `chore:` ビルド・ツール設定等

**例:**
```
feat: Vertex AI Search クライアントを実装

- tenacityによるリトライ処理を追加
- 構造化ログ出力に対応
- 型ヒント・docstringを完備
```

---

## 5. テスト方針

「動くこと」と「正しいこと」を証明するために、体系的なテストを導入します。

### 5.1 テストフレームワーク

**採用:** pytest

**理由:**
- コードが簡潔に書ける
- fixture（テストの前準備・後処理）などの強力な機能が豊富

### 5.2 カバレッジ目標

**目標:** コアロジック（`src/common/`）のカバレッジ **85%以上**

プロトタイプ段階���は網羅性よりも、クリティカルな部分の品質を担保することを優先します。

### 5.3 テストの使い分け

| テスト種別 | 目的 | 配置場所 | モック使用 |
|----------|------|---------|----------|
| **Unit Test**<br>（単体テスト） | 関数・クラス単体の動作検証 | `tests/common/`, `tests/phase1/`, `tests/phase2/` | ✅ 外部APIはモック化 |
| **Integration Test**<br>（結合テスト） | 複数モジュールの連携動作検証 | `tests/integration/` | △ 必要に応じて |
| **E2E Test**<br>（エンドツーエンド） | 実環境での一連の流れの検証<br>（例: Twitterメンション→Bot返信） | `tests/e2e/` | ❌ 実環境使用 |

**Unit Test 例:**
```python
from unittest.mock import patch
from src.common.vertex_search import VertexAISearchClient

def test_search_with_retry():
    """リトライ処理が正しく動作するか"""
    with patch('src.common.vertex_search.DiscoveryServiceClient') as mock:
        mock.return_value.search.side_effect = [Exception("Network Error"), {"results": []}]
        client = VertexAISearchClient()
        result = client.search("query")
        assert result == {"results": []}
        assert mock.return_value.search.call_count == 2  # リトライされたか
```

---

## 6. プロジェクト独自ルール

本プロジェクトを成功に導くための、特に重視したい点です。

### 6.1 最重要視点

**免責事項の徹底:**
- AIによる生成回答である旨と、100%の正確性を保証しない旨の免責事項は、**全ての回答生成パスにおいて必ず付与**
- `src/common/disclaimer.py` に共通関数を実装
- テストで免責事項の存在を検証
- **これは本プロジェクトの信頼性を守る生命線です**

**コスト意識:**
- Cloud Runのインスタンス数やVertex AIの呼び出し回数はコストに直結
- 非効率なループ処理や不要なAPI呼び出しがないか常に意識
- ログレベルは本番環境では INFO 以上に設定

### 6.2 チームメンバーとの共有ルール

**環境構築手順の明文化:**
- `docs/development_setup.md` に git clone からテスト実行まで記載
- 誰でも迷わず開発環境を構築できるようにする

**機密情報の取り扱い:**
- Twitter APIキーやGCP関連キーの具体的な取り扱い手順をドキュメント化
- Secret Managerへの登録方法、IAMロールの設定方法を明記
- チーム全員で遵守

**Whyの共有:**
- 新しい技術やライブラリを導入する際は、必ず「理由（Why）」をPRやドキュメントに明記
- なぜそれが必要なのかをチームで共有

---

## 7. チェックリスト

### 新規実装時

- [ ] 型ヒントを全ての関数に付与したか？
- [ ] Googleスタイルのdocstringを記述したか？
- [ ] 外部API呼び出しにリトライ処理を実装したか？
- [ ] タイムアウト設定を行ったか？
- [ ] 構造化ログ（JSON形式）で出力しているか？
- [ ] 免責事項を付与する共通関数を使用したか？（回答生成の場合）
- [ ] 認証情報をコード内に直接記述していないか？
- [ ] Unit Testを作成したか？

### PR作成時

- [ ] `black` と `isort` でフォーマットしたか？
- [ ] `mypy` で型チェックをパスしたか？
- [ ] `pytest` で全テストがパスしたか？
- [ ] カバレッジが基準を満たしているか？（`src/common/` は85%以上）
- [ ] Conventional Commits形式でコミットメッセージを記述したか？
- [ ] PRテンプレートの項目を全て埋めたか？
- [ ] 変更の「Why（なぜ）」を説明したか？

---

## 補足: 開発環境

### Python バージョン
- **3.11以上**を推奨

### 仮想環境管理
- `venv` または `poetry` を使用
- チームで統一すること

### 依存関係管理
- `requirements.txt` で管理
- 必要に応じて `requirements-dev.txt`（開発用）を分離

### 推奨ツール
```bash
# フォーマッタ・リンター
pip install black isort mypy

# テスト
pip install pytest pytest-cov

# リトライ
pip install tenacity

# GCP SDK
pip install google-cloud-aiplatform google-cloud-secret-manager
```

---

**このルールを守ることで、技術的負債を最小限に抑えつつ、迅速かつ堅牢なプロトタイプ開発を実現します。**

---

## 8. GovGovWeb と govgovbot の開発における重要な注意事項

### 8.1 バックエンドロジックの修正禁止

**重要: GovGovWebではバックエンドロジックを実装しない**

- ❌ **NG**: `src/common/` 内のファイルを修正してテキスト整形や RAG 呼び出しを実装
- ❌ **NG**: GovGovWeb 独自の回答生成ロジックを追加
- ✅ **OK**: UI/UX の改善（デザイン、ストリーミング表示の調整など）
- ✅ **OK**: 新しい API エンドポイントを govgovbot に追加してもらい、それを呼び出す

**理由:**
- テキスト整形ロジックは govgovbot の `twitter_listener.py` に一元化
- 同じロジックを2箇所に実装すると、メンテナンスコストが倍増
- govgovbot 側で修正すれば、Twitter Bot と Web UI の両方に自動反映される

### 8.2 テキスト整形の問題が発生した場合

**問題報告先:**
- govgovbot チーム、または govgovbot リポジトリに Issue 作成

**修正箇所:**
- `govgovbot/src/phase2/twitter_listener.py` の `_normalize()` 関数

**GovGovWeb側での対応:**
- なし（govgovbot の修正を待つ）
- 必要に応じて、ブラウザ側で CSS での整形を追加（最終手段）

### 8.3 新しい機能の追加フロー

**例: 質問履歴機能を追加したい場合**

1. **govgovbot 側で実装:**
   ```python
   # govgovbot/src/phase2/main.py
   @app.post("/api/history")
   def api_history() -> Any:
       """質問履歴を取得"""
       # DBから履歴を取得するロジック
       return jsonify({"ok": True, "history": [...]})
   ```

2. **GovGovWeb 側で API Route を作成:**
   ```typescript
   // GovGovWeb/webapp/app/api/history/route.ts
   export async function POST(req: Request) {
     const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8080';
     const response = await fetch(`${backendUrl}/api/history`, {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
     });
     return response;
   }
   ```

3. **GovGovWeb 側で UI を実装:**
   ```typescript
   // GovGovWeb/webapp/app/components/History.tsx
   const response = await fetch('/api/history', { method: 'POST' });
   const data = await response.json();
   // 履歴を表示
   ```

### 8.4 ローカル開発時の注意

**必須: govgovbot Flask サーバーを先に起動**

```bash
# Terminal 1: govgovbot を起動（必須）
cd ../govgovbot
source .venv/bin/activate
python -m src.phase2.main
# → http://localhost:8080

# Terminal 2: GovGovWeb を起動
cd GovGovWeb/webapp
npm run dev
# → http://localhost:3000
```

**govgovbot が起動していない場合:**
- Web UI で質問しても回答が返ってこない
- ブラウザの Console に "Failed to fetch" エラーが表示される

### 8.5 環境変数の設定

**`.env.local` (GovGovWeb/webapp/.env.local):**
```bash
# ローカル開発
BACKEND_API_URL=http://localhost:8080

# 本番環境（Cloud Run にデプロイ後）
# BACKEND_API_URL=https://govgovbot-xxxxx-xx.a.run.app
```

**確認方法:**
```bash
# GovGovWeb/webapp ディレクトリで
cat .env.local
```

### 8.6 デプロイ時の注意

**デプロイ順序:**
1. 先に **govgovbot** を Cloud Run にデプロイ
2. デプロイされた URL を確認（例: `https://govgovbot-xxxxx.run.app`）
3. GovGovWeb の環境変数 `BACKEND_API_URL` を更新
4. **GovGovWeb** を Cloud Run にデプロイ

**理由:**
- GovGovWeb は govgovbot の URL を環境変数で指定
- govgovbot がデプロイされていないと、GovGovWeb が動作しない

### 8.7 トラブルシューティング

**症状: Web UI で回答が表示されない**

**確認手順:**
1. ブラウザの開発者ツール → Console タブ
   - エラーメッセージを確認

2. ブラウザの開発者ツール → Network タブ
   - `/api/ask` へのリクエストを確認
   - Status Code が 500 や 404 の場合は、govgovbot が起動していない可能性

3. govgovbot の Flask サーバーが起動しているか確認
   ```bash
   curl http://localhost:8080/healthz
   # 期待: {"ok": true, "health": "ok"}
   ```

4. `/api/ask` エンドポイントが動作しているか確認
   ```bash
   curl -X POST http://localhost:8080/api/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "テスト"}'
   # 期待: {"ok": true, "answer": "...", "sources": [...]}
   ```

5. 環境変数が正しく設定されているか確認
   ```bash
   cat .env.local
   # BACKEND_API_URL=http://localhost:8080 が含まれているか確認
   ```

**症状: テキストの改行がおかしい**

**対応:**
- ❌ GovGovWeb 側で修正しようとしない
- ✅ govgovbot チームに問題を報告
- ✅ govgovbot の `twitter_listener.py` で修正してもらう
- ✅ govgovbot Flask サーバーを再起動すれば、GovGovWeb にも反映される

### 8.8 コード修正時の責任範囲

| 問題の種類 | 修正箇所 | 担当 |
|-----------|---------|------|
| UI/デザインの改善 | GovGovWeb | Web チーム |
| ストリーミング表示の調整 | GovGovWeb | Web チーム |
| テキスト整形（改行、箇条書き） | govgovbot | Bot チーム |
| RAG 呼び出しの改善 | govgovbot | Bot チーム |
| 新しい API エンドポイント | govgovbot → GovGovWeb | Bot チーム → Web チーム |
| 免責事項の文言変更 | govgovbot | Bot チーム |

# プロジェクト設計ルール

このドキュメントは、本プロジェクトにおける設計思想、コーディング規約、運用ルールを定めたものです。
LLMによるコード生成や、チームメンバーによる開発において、常にこのルールに従ってください。

---

## 1. ディレクトリ構造と責務

プロトタイプのフェーズ管理において分かりやすい構造を維持しつつ、コードの再利用性と将来の拡張性を担保します。

### 1.1 全体構造

**重要: govgovbotとgovgovwebの関係性**

本プロジェクトは **govgovbot** と **govgovweb** の2つのアプリケーションから構成されています:

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
│   └── CLAUDE.md          # このファイル（Bot用設計ルール）
│
└── govgovweb/              # Web UI アプリケーション
    ├── webapp/            # Next.js アプリケーション
    │   ├── app/
    │   │   ├── api/ask/route.ts  # API Route (govgovbotのFlaskを呼び出す)
    │   │   └── page.tsx          # メインページUI
    │   └── Dockerfile
    ├── src/
    │   └── common/        # Web独自の共通ロジック（RAGクライアント等）
    └── CLAUDE.md          # Web用設計ルール
```

### 1.2 アーキテクチャの重要な違い

| 項目 | govgovbot | govgovweb |
|------|-----------|-----------|
| **目的** | Twitter Bot として動作 | Webブラウザから利用可能なUI |
| **フロントエンド** | なし（Twitter がUI） | Next.js 14 + TypeScript |
| **バックエンド** | Flask (Python) | Next.js API Routes → **govgovbotのFlaskを呼び出す** |
| **エンドポイント** | `/tweet`, `/tasks/reply-latest`, `/tasks/reply-new-mentions`, **`/api/ask`** | Next.js `/api/ask` → Flask `/api/ask` |
| **デプロイ先** | Google Cloud Run (Flask) + Cloud Functions | Google Cloud Run (Next.js) |
| **応答生成ロジック** | `src/phase2/twitter_listener.py` の `build_rag_reply()` と `_compose_tweet_from_search_result()` | **govgovbotの同じ関数を使用** |
| **テキスト整形** | `_normalize()` 関数で日本語テキストを整形 | **govgovbotの同じ関数を使用** |

### 1.3 コードの共有と依存関係

**重要: テキスト整形ロジックの一元管理**

- **テキスト整形ロジックは `govgovbot/src/phase2/twitter_listener.py` に一元化**
- `_compose_tweet_from_search_result()` 関数が両アプリケーションで使用される
- 改行処理、箇条書き、セクション見出しの整形ロジックは全てこの関数内の `_normalize()` で実装
- **govgovwebはgovgovbotのFlaskサーバーを呼び出すため、コード変更はgovgovbotで実施**

**コード修正時の注意:**
- ❌ **NG**: govgovwebとgovgovbotで別々にテキスト整形ロジックを実装
- ✅ **OK**: govgovbot側でロジックを修正すれば、自動的に両アプリケーションに反映される

### 1.4 govgovbot ディレクトリ構造

```
govgovbot/
├── src/                    # アプリケーションコードの心臓部
│   ├── phase1/            # フェーズ1（コア機能）の実行スクリプト・ロジック（ローカル検証用）
│   ├── phase2/            # フェーズ2（Twitter連携・Cloud Run）のWebアプリケーションコード（Flask）
│   │   ├── main.py                   # Flask アプリケーション定義
│   │   ├── twitter_listener.py       # 【重要】Bot応答生成 + テキスト整形ロジック
│   │   └── twitter_poster.py         # Twitter投稿機能
│   └── common/            # 両フェーズで共通利用するロジック
│                          # - Vertex AI RAG/Search クライアント
│                          # - 回答整形ロジック
│                          # - 設定読み込み
│                          # - 免責事項付与の共通関数
│                          # - リトライデコレータ
│                          # - ログ設定
├── tests/                 # 品質保証の砦
│   ├── phase1/           # フェーズ1のテストコード
│   ├── phase2/           # フェーズ2のテストコード
│   └── common/           # 共通ロジックのテストコード
├── data/                  # 知識の源泉（行政事業レビューデータ、前処理スクリプト）
├── config/                # 設定ファイル置き場（秘匿情報は含めない）
├── scripts/               # セットアップスクリプト
└── docs/                  # 未来の自分たちへの申し送り（設計思想、環境構築手順、API仕様）
```

**重要原則:**
- `src/common/` にコアロジックを集約し、コードの重複を防ぐ
- **テキスト整形ロジックは `src/phase2/twitter_listener.py` に集約（govgovwebも使用）**
- `tests/` の構造は `src/` に対応させる
- 認証情報のような秘匿情報は `config/` に含めず、Secret Manager または `.env`（.gitignore対象）で管理

### 1.5 Flask API エンドポイント一覧

govgovbot の Flask アプリケーション (`src/phase2/main.py`) は以下のエンドポイントを提供:

| エンドポイント | メソッド | 用途 | 呼び出し元 |
|--------------|---------|------|-----------|
| `/` | GET | ヘルスチェック（疎通確認） | Cloud Run, 監視 |
| `/healthz` | GET, HEAD | ヘルスチェック | Cloud Run |
| `/tweet` | POST | ツイート投稿 | 管理ツール |
| `/tasks/reply-latest` | POST | 最新メンションに返信（1件） | Cloud Scheduler |
| `/tasks/reply-new-mentions` | POST | 新着メンション一括処理 | Cloud Scheduler |
| **`/api/ask`** | POST | **Web UIからの質問に回答** | **govgovweb** |

**重要: `/api/ask` エンドポイント**
- govgovweb の Next.js API Route から呼び出される
- リクエスト: `{"question": "質問内容"}`
- レスポンス: `{"ok": true, "answer": "回答", "sources": ["URL1", ...]}`
- 内部で `build_rag_reply()` を使用し、同じテキスト整形ロジックを適用

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

## 8. govgovbot と govgovweb の開発における重要な注意事項

### 8.1 テキスト整形ロジックの修正

**修正が必要な場合の作業場所:**
- ✅ **govgovbot**: `src/phase2/twitter_listener.py` の `_normalize()` 関数を修正
- ❌ **govgovweb**: 修正不要（govgovbot の Flask API を呼び出すため自動反映）

**修正例:**
```python
# govgovbot/src/phase2/twitter_listener.py の _normalize() 関数内

# 改行処理の修正
text = re.sub(r"\n{3,}", "\n\n", text)  # 3つ以上の改行を2つに

# 箇条書き記号の処理
text = re.sub(r"(?<!^)(?<!\n)([\s:：。])([\・\-\*\•])", r"\1\n\2", text, flags=re.MULTILINE)
```

**影響範囲:**
- Twitter Bot の応答
- Web UI の応答（govgovweb 経由）

### 8.2 新しいエンドポイントの追加

**govgovbot に新しい機能を追加する場合:**
1. `src/phase2/main.py` に Flask ルートを追加
2. 必要に応じて `twitter_listener.py` にビジネスロジックを実装
3. govgovweb から呼び出す場合は、`webapp/app/api/` に対応する API Route を追加

**例: 履歴機能の追加**
```python
# govgovbot/src/phase2/main.py
@app.post("/api/history")
def api_history() -> Any:
    """過去の質問履歴を取得"""
    # ロジック実装
    return jsonify({"ok": True, "history": [...]})
```

```typescript
// govgovweb/webapp/app/api/history/route.ts
export async function POST(req: Request) {
  const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8080';
  const response = await fetch(`${backendUrl}/api/history`, { method: 'POST' });
  return response;
}
```

### 8.3 デプロイメント時の注意

**デプロイ順序:**
1. 先に **govgovbot** をデプロイ
2. その後 **govgovweb** をデプロイ

**理由:**
- govgovweb は govgovbot の Flask API に依存
- govgovbot が起動していないと、govgovweb の API 呼び出しが失敗

**環境変数の確認:**
- govgovweb の `BACKEND_API_URL` が正しく設定されているか確認
- 本番環境では Cloud Run の URL を指定

### 8.4 ローカル開発時の起動順序

```bash
# Terminal 1: govgovbot Flask サーバーを起動
cd govgovbot
source .venv/bin/activate  # または venv/Scripts/activate (Windows)
python -m src.phase2.main
# → http://localhost:8080 で起動

# Terminal 2: govgovweb Next.js を起動
cd govgovweb/webapp
npm run dev
# → http://localhost:3000 で起動
```

**確認:**
- http://localhost:3000 にアクセス
- 質問を入力
- Next.js が http://localhost:8080/api/ask を呼び出す
- govgovbot が回答を生成して返す

### 8.5 トラブルシューティング

**症状: govgovweb で回答が表示されない**

**確認項目:**
1. govgovbot の Flask サーバーが起動しているか？
   ```bash
   curl http://localhost:8080/healthz
   # 期待: {"ok": true, "health": "ok"}
   ```

2. `/api/ask` エンドポイントが動作しているか？
   ```bash
   curl -X POST http://localhost:8080/api/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "デジタル庁の予算は？"}'
   # 期待: {"ok": true, "answer": "...", "sources": [...]}
   ```

3. govgovweb の環境変数が正しいか？
   ```bash
   # govgovweb/webapp/.env.local
   BACKEND_API_URL=http://localhost:8080
   ```

4. ブラウザの開発者ツールで Network タブを確認
   - `/api/ask` へのリクエストが失敗していないか？
   - CORS エラーが出ていないか？

**症状: テキストの改行がおかしい**

**確認項目:**
1. 最新の `govgovbot/src/phase2/twitter_listener.py` が反映されているか？
2. Flask サーバーを再起動したか？（コード変更後は再起動必要）
   ```bash
   # Ctrl+C で停止 → 再度起動
   python -m src.phase2.main
   ```

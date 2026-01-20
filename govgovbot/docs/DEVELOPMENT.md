# 開発ガイド

このドキュメントでは、チーム開発のための開発環境のセットアップと開発フローを説明します。

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd govgov
```

### 2. Python仮想環境のセットアップ

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化 (Mac/Linux)
source venv/bin/activate

# 仮想環境を有効化 (Windows)
.\venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt
```

### 3. 環境変数の設定

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集して、必要な値を設定
# GCP関連の設定値はチームリーダーまたは GCP_SETUP.md を参照
```

### 4. GCP認証の設定

GCP環境のセットアップが完了している場合:

```bash
# gcloudにログイン
gcloud auth login

# アプリケーションデフォルト認証
gcloud auth application-default login

# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID
```

## プロジェクト構造

```
govgov/
├── src/
│   ├── __init__.py
│   ├── phase1/              # フェーズ1: コア機能
│   │   ├── __init__.py
│   │   ├── knowledge_source.py    # F-01: ナレッジソース構築
│   │   ├── factcheck.py           # F-03: ファクトチェック実行
│   │   └── cli.py                 # F-02: CLIインターフェース
│   └── phase2/              # フェーズ2: Twitter連携
│       ├── __init__.py
│       ├── twitter_listener.py    # F-04: メンション監視
│       ├── twitter_poster.py      # F-05: 回答投稿
│       └── main.py                # Cloud Run エントリポイント
├── config/                  # 設定ファイル
├── data/                    # ローカルデータ保存用
├── tests/                   # テストコード
│   ├── __init__.py
│   ├── test_phase1/
│   └── test_phase2/
├── docs/                    # ドキュメント
│   ├── GCP_SETUP.md        # GCP環境セットアップガイド
│   └── DEVELOPMENT.md      # 本ファイル
├── requirements.txt         # Python依存関係
├── Dockerfile              # コンテナ定義
├── .env.example            # 環境変数テンプレート
├── .gitignore
└── README.md
```

## 開発フロー

### ブランチ戦略

- `main`: 本番用ブランチ（保護されています）
- `develop`: 開発用メインブランチ
- `feature/*`: 機能開発用ブランチ
- `fix/*`: バグ修正用ブランチ

### 新機能の開発手順

1. **ブランチを作成**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **開発を進める**
   - コードを書く
   - テストを書く
   - ローカルでテストを実行

3. **コミット**
   ```bash
   git add .
   git commit -m "feat: 機能の説明"
   ```

4. **プルリクエストを作成**
   ```bash
   git push origin feature/your-feature-name
   ```
   GitHubでプルリクエストを作成し、レビューを依頼

### コミットメッセージのルール

Conventional Commitsに従います:

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメントのみの変更
- `style:` コードの意味に影響を与えない変更（空白、フォーマットなど）
- `refactor:` バグ修正でも機能追加でもないコード変更
- `test:` テストの追加や修正
- `chore:` ビルドプロセスやツールの変更

例:
```
feat: Vertex AI Search連携機能を追加
fix: ファクトチェック結果のフォーマットエラーを修正
docs: GCPセットアップガイドを更新
```

## テストの実行

### 全テストの実行

```bash
# 仮想環境を有効化
source venv/bin/activate

# pytest実行
pytest

# カバレッジ付き
pytest --cov=src tests/
```

### 特定のテストのみ実行

```bash
# フェーズ1のテストのみ
pytest tests/test_phase1/

# 特定のテストファイル
pytest tests/test_phase1/test_factcheck.py

# 特定のテスト関数
pytest tests/test_phase1/test_factcheck.py::test_basic_query
```

## ローカル開発

### フェーズ1: CLIでのファクトチェック

```bash
# CLIインターフェースを起動
python -m src.phase1.cli

# または、直接質問を投げる
python -m src.phase1.cli --question "デジタル庁の予算は？"
```

### フェーズ2: Flaskサーバーの起動

```bash
# 開発サーバーを起動
export FLASK_APP=src.phase2.main
export FLASK_ENV=development
flask run

# または
python -m src.phase2.main
```

## Dockerでの開発

### イメージのビルド

```bash
docker build -t factcheck-bot .
```

### コンテナの実行

```bash
# フェーズ1（CLI）
docker run -it --rm \
  -v $(pwd)/.env:/app/.env \
  factcheck-bot

# フェーズ2（Webサーバー）
docker run -p 8080:8080 \
  -v $(pwd)/.env:/app/.env \
  factcheck-bot
```

## デバッグ

### ログレベルの設定

`.env` ファイルで設定:

```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### VSCodeでのデバッグ

`.vscode/launch.json` の例:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: CLI",
      "type": "python",
      "request": "launch",
      "module": "src.phase1.cli",
      "args": ["--question", "テスト質問"],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Python: Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "src.phase2.main",
        "FLASK_ENV": "development"
      },
      "args": ["run"],
      "jinja": true
    }
  ]
}
```

## よくある問題と解決方法

### 仮想環境が有効化されない

```bash
# Mac/Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat
```

### インポートエラー

```bash
# Pythonパスを確認
echo $PYTHONPATH

# プロジェクトルートをPythonパスに追加
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### GCP認証エラー

```bash
# 認証情報を再設定
gcloud auth application-default login

# プロジェクトを確認
gcloud config get-value project
```

### 依存関係のバージョン競合

```bash
# 仮想環境を削除して再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## コードスタイル

### フォーマッター

プロジェクトでは `black` を使用します（将来導入予定）:

```bash
# インストール
pip install black

# フォーマット
black src/ tests/
```

### リンター

`flake8` を使用します（将来導入予定）:

```bash
# インストール
pip install flake8

# チェック
flake8 src/ tests/
```

## チーム開発のベストプラクティス

1. **コードレビューは必須**
   - すべてのPRは最低1人のレビューを受ける
   - レビュー後に承認されてからマージ

2. **小さなコミット、頻繁なプッシュ**
   - 大きな変更を小さく分割
   - 定期的にプッシュして進捗を共有

3. **テストを書く**
   - 新機能には必ずテストを追加
   - バグ修正には再現テストを追加

4. **ドキュメントを更新**
   - コード変更に伴いREADMEやドキュメントも更新
   - 複雑なロジックにはコメントを追加

5. **環境変数の管理**
   - `.env` ファイルは絶対にコミットしない
   - `.env.example` は常に最新に保つ

6. **依存関係の管理**
   - 新しいライブラリを追加したら `requirements.txt` を更新
   - バージョンを固定して再現性を確保

## 開発タスク管理

### 現在の開発フェーズ: フェーズ1

優先順位:

1. **F-01: ナレッジソース構築** (高)
   - 行政事業レビューデータの収集スクリプト
   - Cloud Storageへのアップロード
   - Vertex AI Searchへのインポート

2. **F-03: ファクトチェック実行** (高)
   - Vertex AI Search API呼び出し
   - 回答生成ロジック
   - レスポンスフォーマット

3. **F-02: CLIインターフェース** (中)
   - コマンドライン引数のパース
   - 質問の受付と結果の表示

### 次のフェーズ: フェーズ2

1. **F-04: メンション監視** (未着手)
2. **F-05: 回答投稿** (未着手)

## ヘルプとサポート

- 質問: チームSlack/チャットで質問
- バグ報告: GitHubのIssuesを作成
- ドキュメント: `docs/` ディレクトリを参照

## 参考資料

- [README.md](../README.md) - プロジェクト概要
- [GCP_SETUP.md](GCP_SETUP.md) - GCP環境構築
- [要件定義書](../../txt/rd.txt) - 詳細な要件
- [Vertex AI Search ドキュメント](https://cloud.google.com/generative-ai-app-builder/docs)

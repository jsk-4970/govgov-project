# セキュリティガイドライン

**プロジェクト**: govgov (行政事業レビューファクトチェックBot)

このドキュメントは、チーム開発におけるセキュリティのベストプラクティスを定めます。

---

## 🔒 重要: 絶対にコミットしてはいけないもの

以下のファイル・情報は**絶対にGitにコミットしないでください**:

### 1. 環境変数ファイル
- ❌ `.env`
- ❌ `.env.local`
- ❌ `.env.production`
- ❌ `.env.development`
- ✅ `.env.example` のみOK（実際の値を含まないテンプレート）

### 2. GCP認証情報
- ❌ サービスアカウントキー (`*-key.json`, `service-account*.json`)
- ❌ アプリケーションデフォルト認証情報 (`application_default_credentials.json`)
- ❌ クライアントシークレット (`client_secret*.json`)
- ❌ すべての `.json` ファイル（例外: `config/*.example.json`）

### 3. APIキーとトークン
- ❌ Twitter API キー・シークレット
- ❌ GCP APIキー
- ❌ その他すべてのAPIトークン

### 4. 秘密鍵・証明書
- ❌ `.pem`, `.key`, `.p12`, `.pfx` ファイル
- ❌ SSH秘密鍵
- ❌ SSL/TLS証明書の秘密鍵

---

## ✅ .gitignore の確認

`.gitignore` に以下が含まれていることを確認してください:

```gitignore
# Environment variables (CRITICAL - NEVER COMMIT)
.env
.env.local
.env.*.local
.env.development
.env.production
.env.test

# Google Cloud (CRITICAL - NEVER COMMIT CREDENTIALS)
*.json
!config/*.example.json
*-key.json
service-account*.json
credentials.json
client_secret*.json
google-credentials*.json
application_default_credentials.json

# API Keys and Secrets (CRITICAL)
*_api_key*
*_secret*
*.pem
*.key
*.p12
*.pfx
.secret
secrets/
*.credentials
```

---

## 🛡️ セキュリティチェックリスト

### プルリクエスト作成前

- [ ] `.env` ファイルがコミットに含まれていないか確認
- [ ] `git status` でステージングされたファイルを確認
- [ ] `git diff --cached` で変更内容を確認
- [ ] APIキーやパスワードがコード内にハードコードされていないか確認
- [ ] サービスアカウントキーやJSON認証ファイルが含まれていないか確認

### コミット前の確認コマンド

```bash
# ステージングされたファイルを確認
git status

# 機密情報が含まれていないかチェック
git diff --cached | grep -i -E "(api_key|secret|password|token|credentials)"

# .env が追跡されていないか確認
git ls-files | grep .env
# ↑ 何も出力されなければOK
```

---

## 🚨 万が一、機密情報をコミットしてしまった場合

### 1. まだプッシュしていない場合

```bash
# 直前のコミットを取り消し
git reset --soft HEAD~1

# .gitignoreを確認して修正
# 機密ファイルを削除してから再コミット
```

### 2. 既にプッシュしてしまった場合

**即座に以下を実行**:

1. **認証情報を無効化**
   - GCPサービスアカウントキー → GCPコンソールから削除
   - Twitter APIキー → Twitter Developer Consoleから再生成
   - その他APIキー → 各サービスで無効化・再生成

2. **チームリーダーに連絡**
   - 即座に報告
   - 対応方針を相談

3. **Git履歴から削除**（高度な操作 - 慎重に）
   ```bash
   # git-filter-repoを使用（推奨）
   # または管理者に依頼
   ```

---

## 🔑 認証情報の安全な管理方法

### ローカル開発

1. **環境変数ファイル (`.env`)**
   - ローカルマシンにのみ保存
   - チーム内で共有する場合は、安全な方法（暗号化チャット等）で

2. **GCP認証**
   - `gcloud auth application-default login` を使用
   - サービスアカウントキーのダウンロードは避ける
   - 必要な場合は、プロジェクトルート外に保存

### 本番環境

1. **Secret Manager**
   - GCP Secret Managerに保存
   - コードからは環境変数経由でアクセス

2. **Cloud Run環境変数**
   - デプロイ時に設定
   - GCPコンソールまたは `gcloud` コマンドで管理

---

## 👥 チーム開発のベストプラクティス

### 環境変数の共有

**NG（絶対にやらない）**:
- ❌ `.env` ファイルをSlackやメールで送信
- ❌ `.env` ファイルをGitにコミット
- ❌ GitHub Issuesに認証情報を記載

**OK（推奨される方法）**:
- ✅ 必要な値のみを暗号化チャットで個別に共有
- ✅ `.env.example` に必要な変数名だけ記載
- ✅ 各自が自分の認証情報を取得・設定
- ✅ GCP Secret Managerを使用

### コードレビュー時の確認事項

レビュアーは以下を確認:

- [ ] ハードコードされた認証情報がないか
- [ ] `.env` や認証ファイルが追加されていないか
- [ ] コメントやデバッグコードにAPIキーが含まれていないか
- [ ] ログ出力に機密情報が含まれていないか

---

## 📋 セキュリティ監査

定期的に以下を実行:

```bash
# Git履歴に機密情報が含まれていないかスキャン
git log -p | grep -i -E "(api_key|secret|password|token|credentials)"

# 現在のリポジトリ内の機密情報チェック
grep -r -i -E "(api_key|secret|password|token)" --exclude-dir=venv --exclude-dir=.git

# .envファイルが追跡されていないか最終確認
git ls-files | grep .env
```

---

## 🔐 推奨ツール

### Git-secrets
リポジトリに機密情報がコミットされるのを防ぐツール:

```bash
# インストール
brew install git-secrets

# セットアップ
cd /path/to/govgov
git secrets --install
git secrets --register-aws  # AWS用のパターン
git secrets --add 'AIza[0-9A-Za-z_-]{35}'  # GCP APIキーパターン
git secrets --add '[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com'  # OAuth
```

### Pre-commit hooks
コミット前の自動チェック:

```bash
# .git/hooks/pre-commit を作成
#!/bin/bash
if git diff --cached --name-only | grep -E "\.env$"; then
    echo "ERROR: .env file detected in commit!"
    exit 1
fi
```

---

## 📞 問題報告

セキュリティ上の懸念や事故が発生した場合:

1. **即座にチームリーダーに報告**
2. **該当する認証情報を無効化**
3. **影響範囲を特定**
4. **対応記録を残す**

---

## 📚 参考資料

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Google Cloud セキュリティベストプラクティス](https://cloud.google.com/security/best-practices)
- [GitHub セキュリティベストプラクティス](https://docs.github.com/ja/code-security/getting-started/best-practices-for-preventing-data-leaks-in-your-organization)

---

**重要**: セキュリティは全員の責任です。不明な点があれば遠慮なく質問してください。

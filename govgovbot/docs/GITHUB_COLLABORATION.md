# GitHub コラボレーションガイド

**リポジトリ**: `HKobayashi2003/govgov`

---

## 👥 新しいメンバーの追加手順

### 1. GitHubリポジトリへの招待

**実行者**: リポジトリオーナー（@HKobayashi2003）

#### ステップ1: GitHub Webから招待

1. [govgovリポジトリ](https://github.com/HKobayashi2003/govgov) にアクセス

2. **Settings** タブをクリック

3. 左サイドバーの **Collaborators** (または **Manage access**) をクリック

4. **Add people** ボタンをクリック

5. 招待するメンバーのGitHubユーザー名またはメールアドレスを入力:
   - **メールアドレス**: `hayakoba.0819@gmail.com`
   - または **GitHubユーザー名**: （相手に確認）

6. **Role** を選択:
   - `Write` - プッシュ権限あり（推奨）
   - `Maintain` - より広い権限
   - `Admin` - 全権限（慎重に）

7. **Add [username] to this repository** をクリック

#### ステップ2: 招待メール

招待されたメンバー（hayakoba.0819@gmail.com）に以下が届きます:
- GitHubからの招待メール
- メール内の **View invitation** リンクをクリックして承認

---

## 📋 新メンバーのオンボーディング

招待が承認されたら、以下をメンバーに共有してください:

### 1. リポジトリのクローン

```bash
# SSHの場合（推奨）
git clone git@github.com:HKobayashi2003/govgov.git
cd govgov

# HTTPSの場合
git clone https://github.com/HKobayashi2003/govgov.git
cd govgov
```

### 2. 開発環境のセットアップ

以下のドキュメントに従ってセットアップ:

1. **[README.md](../README.md)** - プロジェクト概要
2. **[docs/DEVELOPMENT.md](DEVELOPMENT.md)** - 開発環境セットアップ
3. **[docs/SECURITY.md](SECURITY.md)** - セキュリティガイドライン（必読）
4. **[docs/GCP_SETUP_COMPLETE.md](GCP_SETUP_COMPLETE.md)** - GCP環境情報

### 3. 必要な環境変数の設定

`.env.example` をコピーして `.env` を作成:

```bash
cp .env.example .env
```

**必要な値**（チームリーダーから個別に共有）:
- `GCP_PROJECT_ID` - 既に設定済み: `govgov-473916`
- `VERTEX_AI_SEARCH_DATASTORE_ID` - （セットアップ後に設定）
- `VERTEX_AI_SEARCH_ENGINE_ID` - （セットアップ後に設定）
- その他のTwitter API関連（フェーズ2で必要）

### 4. GCP認証

各自のGoogleアカウントで認証:

```bash
# gcloud認証
gcloud auth login

# アプリケーションデフォルト認証
gcloud auth application-default login

# プロジェクト設定
gcloud config set project govgov-473916
```

---

## 🔄 開発ワークフロー

### ブランチ戦略

- `main` - 本番用（保護ブランチ、直接プッシュ不可）
- `develop` - 開発用メインブランチ
- `feature/*` - 機能開発用
- `fix/*` - バグ修正用

### 新機能開発の流れ

```bash
# 1. 最新のdevelopを取得
git checkout develop
git pull origin develop

# 2. フィーチャーブランチを作成
git checkout -b feature/your-feature-name

# 3. 開発作業
# ... コードを書く ...

# 4. コミット（セキュリティチェック必須）
git status  # ステージング確認
git diff --cached  # 変更内容確認
git commit -m "feat: 機能の説明"

# 5. プッシュ
git push origin feature/your-feature-name

# 6. GitHub上でPull Request作成
# → レビュー → 承認 → マージ
```

---

## ✅ プルリクエストのベストプラクティス

### PRを作成する前に

- [ ] **セキュリティチェック**: [docs/SECURITY.md](SECURITY.md) のチェックリストを確認
- [ ] `.env` や認証ファイルが含まれていないか確認
- [ ] テストが通ることを確認: `pytest`
- [ ] コードが動作することを確認
- [ ] コミットメッセージがConventional Commitsに従っているか確認

### PR作成時

- **タイトル**: `feat: ファクトチェック機能を実装` のように明確に
- **説明**:
  - 何を変更したか
  - なぜ変更したか
  - テスト方法
  - スクリーンショット（UIの場合）

### レビュー時

レビュアーは以下を確認:
- [ ] コードの品質
- [ ] セキュリティ（機密情報の漏洩）
- [ ] テストの有無
- [ ] ドキュメントの更新

---

## 🔒 セキュリティルール（必読）

### 絶対に守ること

1. **`.env` ファイルは絶対にコミットしない**
2. **GCP認証ファイル（`*.json`）は絶対にコミットしない**
3. **APIキー・シークレットをコードにハードコードしない**
4. **コミット前に `git status` と `git diff --cached` で確認**

詳細: [docs/SECURITY.md](SECURITY.md)

### コミット前チェックコマンド

```bash
# 機密情報チェック
git diff --cached | grep -i -E "(api_key|secret|password|token|credentials)"

# .envが追跡されていないか確認
git ls-files | grep .env  # 何も出力されなければOK
```

---

## 📞 コミュニケーション

### 質問・相談

- **技術的な質問**: GitHub Issues
- **緊急の連絡**: Slack/チャット
- **セキュリティインシデント**: 即座にチームリーダーに連絡

### 進捗報告

- 定期的に自分のブランチをプッシュ
- PRは早めに作成（Draft PRでもOK）
- ブロッカーがあれば早めに共有

---

## 🎯 タスク管理

### GitHub Issues

新しいタスクや機能追加は Issue として作成:

1. [Issues タブ](https://github.com/HKobayashi2003/govgov/issues) を開く
2. **New issue** をクリック
3. タイトルと説明を記入
4. ラベルを設定（bug, enhancement, documentationなど）
5. 担当者を割り当て

### Project Board（オプション）

チームで使用する場合、GitHub Projectsでタスク管理:
- To Do
- In Progress
- In Review
- Done

---

## 🚨 トラブルシューティング

### コンフリクトが発生した場合

```bash
# 1. 最新のdevelopを取得
git checkout develop
git pull origin develop

# 2. フィーチャーブランチに戻る
git checkout feature/your-feature

# 3. developをマージ
git merge develop

# 4. コンフリクトを解決
# ... ファイルを編集 ...

# 5. コミット
git add .
git commit -m "fix: merge conflict resolved"
git push origin feature/your-feature
```

### 誤って機密情報をコミットした場合

**即座に**: [docs/SECURITY.md](SECURITY.md) の「万が一、機密情報をコミットしてしまった場合」を参照

---

## 📚 参考ドキュメント

- [README.md](../README.md) - プロジェクト概要
- [docs/DEVELOPMENT.md](DEVELOPMENT.md) - 開発ガイド
- [docs/SECURITY.md](SECURITY.md) - セキュリティガイドライン
- [docs/GCP_SETUP.md](GCP_SETUP.md) - GCP環境構築
- [NEXT_STEPS.md](../NEXT_STEPS.md) - 次のステップ

---

## ✨ 成功のためのヒント

1. **頻繁にコミット・プッシュ**: 小さな変更でもコミット
2. **PRは小さく**: 大きな変更は複数のPRに分割
3. **コードレビューを活用**: 学びの機会
4. **質問を恐れない**: わからないことはすぐ聞く
5. **ドキュメントを更新**: コード変更時はドキュメントも更新

---

**Welcome to the team! 🎉**

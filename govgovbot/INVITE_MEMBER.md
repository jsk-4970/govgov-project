# 新メンバー招待手順

**招待するメンバー**: `hayakoba.0819@gmail.com`

---

## 📋 招待手順（リポジトリオーナー実施）

### ステップ1: GitHubで招待

1. **リポジトリにアクセス**
   - https://github.com/HKobayashi2003/govgov

2. **Settings タブをクリック**

3. **Collaborators をクリック**
   - 左サイドバーの「Collaborators」または「Manage access」

4. **Add people をクリック**

5. **メールアドレスを入力**
   ```
   hayakoba.0819@gmail.com
   ```

6. **権限を選択**
   - 推奨: **Write** (プッシュ権限あり)

7. **Add [username] to this repository をクリック**

### ステップ2: 招待メールの確認

hayakoba.0819@gmail.com 宛てに招待メールが送信されます。
メンバーは「View invitation」をクリックして招待を承認する必要があります。

---

## 📧 新メンバーに送るメッセージ（テンプレート）

```
件名: govgovプロジェクトへの招待

こんにちは！

行政事業レビューファクトチェックBot「govgov」プロジェクトにあなたを招待しました。

【リポジトリ】
https://github.com/HKobayashi2003/govgov

【手順】
1. GitHubから届いた招待メールの「View invitation」をクリック
2. 招待を承認
3. リポジトリをクローン:
   git clone git@github.com:HKobayashi2003/govgov.git

【セットアップガイド】
リポジトリをクローンしたら、以下のドキュメントを順番に読んでください:

1. README.md - プロジェクト概要
2. docs/SECURITY.md - セキュリティガイドライン（必読！）
3. docs/GITHUB_COLLABORATION.md - 開発ワークフロー
4. docs/DEVELOPMENT.md - 開発環境セットアップ
5. NEXT_STEPS.md - 現在の進捗と次のステップ

【重要】
- .env ファイルは絶対にコミットしないでください
- 認証情報（*.json）も絶対にコミットしないでください
- 詳細は docs/SECURITY.md を必ず確認してください

【GCP設定】
GCPプロジェクトID: govgov-473916
認証設定が必要です。セットアップガイドを参照してください。

質問があれば気軽に聞いてください！

よろしくお願いします。
```

---

## ✅ 招待完了後のチェックリスト

- [ ] GitHub上で招待を送信
- [ ] メンバーが招待を承認
- [ ] メンバーにウェルカムメッセージを送信
- [ ] 以下のドキュメントを案内:
  - [ ] docs/SECURITY.md（必読）
  - [ ] docs/GITHUB_COLLABORATION.md
  - [ ] docs/DEVELOPMENT.md
  - [ ] NEXT_STEPS.md
- [ ] GCPプロジェクトへのアクセス権限（必要に応じて）
- [ ] Slack/チャットグループに追加（使用している場合）

---

## 🔐 メンバーに共有する環境変数

**共有方法**: 安全な方法（暗号化チャット、直接会って）で以下を共有:

```env
# 既に設定済みの値
GCP_PROJECT_ID=govgov-473916
GCP_LOCATION=asia-northeast1
GCS_BUCKET_NAME=govgov-473916-data

# まだ未設定（Vertex AI Searchセットアップ後）
VERTEX_AI_SEARCH_DATASTORE_ID=（後で設定）
VERTEX_AI_SEARCH_ENGINE_ID=（後で設定）
```

**注意**:
- .envファイル自体は送らない
- 値のみを個別に共有
- Slackやメールで平文で送らない

---

## 📚 参考リンク

- [GitHub Collaboration Guide](docs/GITHUB_COLLABORATION.md)
- [Security Guidelines](docs/SECURITY.md)
- [Development Guide](docs/DEVELOPMENT.md)

---

**招待完了後、このファイルは削除してもOKです**

# ベースイメージとして公式のPythonイメージを使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数の設定（Cloud Run用）
ENV PORT=8080

# Cloud Run / Docker 実行時のHTTPサーバーエントリポイント
# --timeout 300: ストリーミングレスポンス対応のため300秒に設定
# --workers 2: 複数リクエストの同時処理を可能に
# --worker-class sync: 同期workerを使用
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--timeout", "300", "--workers", "2", "--worker-class", "sync", "src.phase2.main:app"]

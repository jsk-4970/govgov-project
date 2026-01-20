FROM python:3.11-slim

WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードコピー
COPY main.py .
# src/commonを含むファイル構造をコピー
COPY . .

# Cloud Run用エントリーポイント (Flaskアプリ)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 1 --timeout 3600 'main:create_app()'

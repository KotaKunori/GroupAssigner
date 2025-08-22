# Python 3.11を使用（OR-Toolsとの互換性向上）
FROM python:3.11-bookworm

WORKDIR /usr/src/app
ENV FLASK_APP=app

# 必要なシステム依存関係をインストール
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       coinor-cbc \
       build-essential \
       pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY /app/requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 作業ディレクトリを設定
WORKDIR /usr/src/app
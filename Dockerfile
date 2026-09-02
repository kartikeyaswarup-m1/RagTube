FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    curl \
    wget \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install python deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# copy app
COPY . /app

# Ensure vectorstore dir exists and is writable
RUN mkdir -p /app/backend/vectorstore && chown -R www-data:www-data /app/backend/vectorstore || true

EXPOSE 8080

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]

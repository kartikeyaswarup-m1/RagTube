FROM python:3.11-slim

WORKDIR /app

# Install system deps required for some Python packages (faiss etc.)
RUN apt-get update && apt-get install -y build-essential git curl unzip && rm -rf /var/lib/apt/lists/*

# yt-dlp uses Deno to solve current YouTube JavaScript challenges.
RUN curl -fsSL https://deno.land/install.sh | sh -s -- -y && \
	ln -s /root/.deno/bin/deno /usr/local/bin/deno

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PORT=8000
EXPOSE 8000

# Use shell form so environment variable expansion happens at container runtime
# Render provides the PORT env var; fall back to 8000 if not set.
CMD sh -c "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

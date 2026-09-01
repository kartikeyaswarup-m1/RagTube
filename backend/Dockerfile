FROM python:3.11-slim

WORKDIR /app

# Install system deps required for some Python packages (faiss etc.)
RUN apt-get update && apt-get install -y build-essential git curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PORT=8000
EXPOSE ${PORT}

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "${PORT}"]

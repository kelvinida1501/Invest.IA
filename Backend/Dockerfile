FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Requisitos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

ENV PYTHONUNBUFFERED=1

# Sobe migrations e inicia a API
# Se não usar Alembic, remova a linha de upgrade.
CMD bash -lc "alembic upgrade head || true; uvicorn app.main:app --host 0.0.0.0 --port 8000"

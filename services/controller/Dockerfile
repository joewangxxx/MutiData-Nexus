FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/controller

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "alembic>=1.14" \
    "fastapi>=0.115" \
    "pydantic>=2.11" \
    "psycopg[binary]>=3.2" \
    "sqlalchemy>=2.0" \
    "uvicorn>=0.34"

COPY db /app/db
COPY services/controller /app/services/controller

WORKDIR /app/services/controller

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

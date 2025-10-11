# api/Dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] pytest httpx ruff black \
    sqlalchemy alembic psycopg2-binary pydantic \
    passlib[argon2] python-jose[cryptography] \
    email-validator python-multipart

ARG VERSION="0.0.0-dev"
ENV APP_VERSION="${VERSION}"
RUN printf "%s" "${APP_VERSION}" > /app/VERSION


COPY app /app/app
COPY tests /app/tests
COPY pyproject.toml /app/pyproject.toml

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

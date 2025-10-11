# api/Dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip
# NOTE: for a lean runtime image, you'd drop pytest/ruff/black later.
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy alembic psycopg2-binary pydantic \
    passlib[argon2] python-jose[cryptography] email-validator python-multipart \
    pytest httpx ruff black

# Bake version from CI
ARG VERSION="0.0.0-dev"
ENV APP_VERSION="${VERSION}"
RUN printf "%s" "${APP_VERSION}" > /app/VERSION

# App source
COPY app /app/app
COPY tests /app/tests
COPY pyproject.toml /app/pyproject.toml

EXPOSE 8000

# Simple container healthcheck hitting FastAPI /health
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/health >/dev/null || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

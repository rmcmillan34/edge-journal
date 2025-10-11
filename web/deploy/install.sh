#!/usr/bin/env bash
set -euo pipefail

OWNER="${EDGEJ_OWNER:-youruser}"      # change default to your GH user/org
VERSION="${EDGEJ_VERSION:-latest}"    # set EDGEJ_VERSION=v0.2.3 to pin
COMPOSE_FILE="${COMPOSE_FILE:-compose.yaml}"

command -v docker >/dev/null || { echo "Docker is required."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required."; exit 1; }

cd "$(dirname "$0")"

# Create .env if missing and generate a strong JWT secret
if [ ! -f ".env" ]; then
  echo "Creating .env from template…"
  cp .env.example .env
  if command -v openssl >/dev/null; then
    sed -i.bak "s/CHANGE_ME_TO_A_LONG_RANDOM_STRING/$(openssl rand -hex 32)/" .env || true
  fi
fi

echo "Pulling images ghcr.io/${OWNER}/edge-journal-{api,web}:${VERSION}…"
docker pull ghcr.io/${OWNER}/edge-journal-api:${VERSION}
docker pull ghcr.io/${OWNER}/edge-journal-web:${VERSION}

EDGEJ_OWNER="${OWNER}" EDGEJ_VERSION="${VERSION}" docker compose -f "${COMPOSE_FILE}" up -d

echo "✅ Edge Journal is running:
- API:  http://localhost:8000/health   and   /version
- Web:  http://localhost:3000
Stop with: docker compose -f ${COMPOSE_FILE} down"

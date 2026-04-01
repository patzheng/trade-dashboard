#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is required" >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo ".env not found in the runner workspace." >&2
  exit 1
fi

echo "[1/3] Building images..."
docker compose build

echo "[2/3] Recreating services..."
docker compose up -d --remove-orphans

echo "[3/3] Current status:"
docker compose ps

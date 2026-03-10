#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Copy .env.example to .env and update values." >&2
  exit 1
fi

cmd="${1:-up}"
shift || true

case "$cmd" in
  up)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build "$@"
    ;;
  down)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down "$@"
    ;;
  logs)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f "$@"
    ;;
  ps)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps "$@"
    ;;
  restart)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" restart "$@"
    ;;
  *)
    echo "Usage: $0 {up|down|logs|ps|restart} [args...]" >&2
    exit 1
    ;;
esac

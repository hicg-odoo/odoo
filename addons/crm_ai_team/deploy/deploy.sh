#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

ensure_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ROOT_DIR/.env.example" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example"
  fi
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

cmd="${1:-quickstart}"
shift || true

case "$cmd" in
  quickstart)
    ensure_env
    compose up -d --build db odoo
    source "$ENV_FILE"
    echo "\nOdoo is starting. Open: http://localhost:${ODOO_HTTP_PORT:-8069}"
    echo "Tip: run './deploy.sh logs odoo' to follow startup logs."
    ;;
  up)
    ensure_env
    compose up -d --build "$@"
    ;;
  up-mcp)
    ensure_env
    compose --profile mcp up -d --build "$@"
    ;;
  seed-demo)
    ensure_env
    source "$ENV_FILE"
    compose exec -T odoo odoo shell \
      --db_host=db \
      --db_user="${POSTGRES_USER:-odoo}" \
      --db_password="${POSTGRES_PASSWORD:-odoo}" \
      -d "${ODOO_DB:-odoo}" <<'PY'
result = env['crm.ai.agent.team'].create_dummy_dataset(team_name='Local Demo Team', agent_count=5, transcript_count=15, auto_run=True)
print(result)
PY
    ;;
  down)
    ensure_env
    compose down "$@"
    ;;
  logs)
    ensure_env
    compose logs -f "$@"
    ;;
  ps)
    ensure_env
    compose ps "$@"
    ;;
  restart)
    ensure_env
    compose restart "$@"
    ;;
  *)
    echo "Usage: $0 {quickstart|up|up-mcp|seed-demo|down|logs|ps|restart} [args...]" >&2
    exit 1
    ;;
esac

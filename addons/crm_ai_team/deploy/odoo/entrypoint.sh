#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-odoo}"
DB_PASSWORD="${DB_PASSWORD:-odoo}"
ODOO_DB="${ODOO_DB:-odoo}"

run_odoo() {
  odoo --db_host="$DB_HOST" --db_port="$DB_PORT" --db_user="$DB_USER" --db_password="$DB_PASSWORD" --database="$ODOO_DB" "$@"
}

echo "[crm_ai_team] initializing module on database: $ODOO_DB"
run_odoo --init=crm_ai_team --without-demo=all --stop-after-init

echo "[crm_ai_team] starting Odoo server"
exec odoo --db_host="$DB_HOST" --db_port="$DB_PORT" --db_user="$DB_USER" --db_password="$DB_PASSWORD" --database="$ODOO_DB" --update=crm_ai_team --without-demo=all

# Local Testing Guide for `crm_ai_team`

This guide is focused on **quick local validation in a browser** plus a few useful checks.

## 1) Prerequisites

- Docker + Docker Compose
- Port `8069` available (or adjust in `.env`)

On Windows, use **Docker Desktop** and PowerShell.

## 2) Start locally (browser-ready)

```bash
cd addons/crm_ai_team/deploy
./deploy.sh quickstart
```

Windows PowerShell:

```powershell
cd addons/crm_ai_team/deploy
.\deploy.ps1 quickstart
```

What this does:
- starts Postgres
- starts Odoo
- auto-installs/updates `crm_ai_team`

Open Odoo:
- `http://localhost:8069` (or `ODOO_HTTP_PORT` from `.env`)

## 3) Seed realistic demo data

```bash
cd addons/crm_ai_team/deploy
./deploy.sh seed-demo
```

Windows PowerShell:

```powershell
cd addons/crm_ai_team/deploy
.\deploy.ps1 seed-demo
```

This creates:
- AI team + agents
- customers and opportunities
- meeting transcripts
- conversation summaries
- run telemetry/logs

In Odoo UI, go to CRM → **AI Relationship Ops**.

## 4) Optional: start MCP server for integration testing

```bash
cd addons/crm_ai_team/deploy
./deploy.sh up-mcp
```

Windows PowerShell:

```powershell
cd addons/crm_ai_team/deploy
.\deploy.ps1 up-mcp
```

This starts the `mcp-server` container using credentials from `.env`.

## 5) Run module tests

If your environment has full Odoo Python dependencies:

```bash
python3 odoo-bin -d crm_ai_team_test --init=crm_ai_team --test-enable --test-tags /crm_ai_team --stop-after-init --without-demo=all
```

Tests cover:
- agent pipeline execution + logging
- churn signal generation on negative sentiment
- transcript processing into summaries/themes
- dummy dataset generation

## 6) Useful operational commands

```bash
cd addons/crm_ai_team/deploy
./deploy.sh ps
./deploy.sh logs odoo
./deploy.sh logs mcp-server
./deploy.sh restart odoo
./deploy.sh down
```

Windows PowerShell:

```powershell
cd addons/crm_ai_team/deploy
.\deploy.ps1 ps
.\deploy.ps1 logs odoo
.\deploy.ps1 logs mcp-server
.\deploy.ps1 restart odoo
.\deploy.ps1 down
```

## 7) Fast troubleshooting

- Odoo not opening?
  - `./deploy.sh logs odoo`
  - check port conflicts (`8069`)
- Empty dataset?
  - run `./deploy.sh seed-demo`
- MCP auth errors?
  - verify `.env` values: `ODOO_ADMIN_USERNAME`, `ODOO_ADMIN_PASSWORD`, `ODOO_DB`

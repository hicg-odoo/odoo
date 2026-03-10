# Deploying `crm_ai_team` locally (fast)

## Deployment options

1. **Copy addon into an existing Odoo instance + update module**
   - Fast if you already run Odoo.
   - Lowest reproducibility.

2. **Package addon as Python/wheel artifact**
   - Good for internal artifact pipelines.
   - More setup complexity for addon path and runtime parity.

3. **Containerized stack (recommended and implemented)**
   - One command spin-up with pinned services.
   - Reproducible local/staging behavior.

## What this package provides

- `odoo/Dockerfile`: Odoo image with `crm_ai_team` + `mcp` installed.
- `odoo/entrypoint.sh`: auto-initializes/updates `crm_ai_team` at container start.
- `docker-compose.yml`: `db`, `odoo`, and optional `mcp-server` profile.
- `.env.example`: local config template.
- `deploy.sh`: quick local lifecycle wrapper.

## Quick local browser testing

```bash
cd addons/crm_ai_team/deploy
./deploy.sh quickstart
```

Windows PowerShell:

```powershell
cd addons/crm_ai_team/deploy
.\deploy.ps1 quickstart
```

Then open:

- Odoo: `http://localhost:8069` (or `ODOO_HTTP_PORT` from `.env`)

## Optional: start MCP too

```bash
./deploy.sh up-mcp
```

Windows PowerShell:

```powershell
.\deploy.ps1 up-mcp
```

## Seed realistic demo records

This creates teams, agents, transcripts, summaries, opportunities and run telemetry:

```bash
./deploy.sh seed-demo
```

Windows PowerShell:

```powershell
.\deploy.ps1 seed-demo
```

## Useful commands

```bash
./deploy.sh ps
./deploy.sh logs odoo
./deploy.sh logs mcp-server
./deploy.sh down
```

Windows PowerShell:

```powershell
.\deploy.ps1 ps
.\deploy.ps1 logs odoo
.\deploy.ps1 logs mcp-server
.\deploy.ps1 down
```

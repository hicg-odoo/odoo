# Deploying `crm_ai_team` repeatedly

## Options

1. **Direct module copy + Odoo service restart**
   - Copy `addons/crm_ai_team` into an existing Odoo addons path.
   - Run Odoo with `--update=crm_ai_team` on each release.
   - ✅ Simple for existing deployments.
   - ❌ Least reproducible across environments.

2. **Python package/wheel distribution**
   - Package the module as a Python artifact and install via `pip`.
   - ✅ Integrates with artifact repositories.
   - ❌ More packaging overhead for Odoo addon path resolution.

3. **Containerized deployment (recommended / implemented here)**
   - Build a versioned Odoo image that includes `crm_ai_team` and MCP dependency.
   - Use Docker Compose for Postgres + Odoo init + Odoo runtime + MCP server.
   - ✅ Most reproducible and easiest to run repeatedly in dev/stage/prod.

## Implemented solution

This directory provides a repeatable deployment package:

- `odoo/Dockerfile`: Builds an Odoo image with `crm_ai_team` preloaded and `mcp` installed.
- `docker-compose.yml`: Defines `db`, `odoo-init`, `odoo-runtime`, and `mcp-server` services.
- `.env.example`: Deployment variables template.
- `deploy.sh`: Convenience wrapper around common `docker compose` commands.

## Quick start

```bash
cd addons/crm_ai_team/deploy
cp .env.example .env
./deploy.sh up
```

Open Odoo at `http://localhost:8069` (or `ODOO_HTTP_PORT`).

## Re-deploying new versions

1. Pull new code.
2. Rebuild/restart:

```bash
cd addons/crm_ai_team/deploy
./deploy.sh up
```

Compose rebuilds the image and updates running containers.

## Operational commands

```bash
./deploy.sh ps
./deploy.sh logs odoo-runtime
./deploy.sh logs mcp-server
./deploy.sh down
```

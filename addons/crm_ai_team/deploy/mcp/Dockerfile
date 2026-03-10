FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir mcp

COPY ./addons/crm_ai_team /app/crm_ai_team

CMD ["python", "/app/crm_ai_team/tools/mcp_server.py"]

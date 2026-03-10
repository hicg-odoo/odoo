FROM odoo:18.0

USER root
RUN pip3 install --no-cache-dir mcp

COPY ./addons/crm_ai_team /mnt/extra-addons/crm_ai_team

USER odoo

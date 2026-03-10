FROM odoo:18.0

USER root
RUN pip3 install --no-cache-dir mcp

COPY ./addons/crm_ai_team /mnt/extra-addons/crm_ai_team
COPY ./addons/crm_ai_team/deploy/odoo/entrypoint.sh /usr/local/bin/crm-ai-team-entrypoint.sh
RUN chmod +x /usr/local/bin/crm-ai-team-entrypoint.sh

USER odoo
ENTRYPOINT ["/usr/local/bin/crm-ai-team-entrypoint.sh"]

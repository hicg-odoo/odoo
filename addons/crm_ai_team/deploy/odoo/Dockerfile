FROM odoo:18.0

USER root

COPY ./addons/crm_ai_team /mnt/extra-addons/crm_ai_team
COPY ./addons/crm_ai_team/deploy/odoo/entrypoint.sh /usr/local/bin/crm-ai-team-entrypoint.sh
RUN chown odoo:odoo /usr/local/bin/crm-ai-team-entrypoint.sh && chmod +x /usr/local/bin/crm-ai-team-entrypoint.sh

USER odoo
ENTRYPOINT ["/usr/local/bin/crm-ai-team-entrypoint.sh"]

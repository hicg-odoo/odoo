CRM AI Agent Team
=================

This module provides an architecture foundation for managing customer relationships with an AI agent team.

Core building blocks
--------------------

* **AI Agent Team**: groups specialized agents (sales, renewal, support, risk).
* **AI Agent**: stores role and instruction/prompt for each participant agent.
* **Conversation Summary**: captures customer interaction summaries with sentiment and extracted key points.
* **Conversation Theme**: classifies reusable themes such as cross-sell, upsell, renewal, and churn risk.
* **Relationship Signal**: tracks structured recommendations and risk/opportunity indicators detected by agents.

Linkage to business records
---------------------------

Conversation summaries and relationship signals can be linked to:

* CRM opportunities (`crm.lead`)
* Reference cases/tickets via a dynamic reference field (`helpdesk.ticket`, `project.task`, or `crm.lead` when available)

This allows AI output to flow into both sales and case-management workflows.

MCP server
----------

The module includes a lightweight MCP server implementation at
``addons/crm_ai_team/tools/mcp_server.py`` that can call key Odoo models via XML-RPC.
It requires the Python package ``mcp`` to be installed in the runtime environment.

Exposed tools include:

* ``list_conversation_summaries``
* ``create_conversation_summary``
* ``create_relationship_signal``
* ``list_sales_opportunities``
* ``run_agent_team``
* ``get_observability_snapshot``
* ``ingest_meeting_transcript``
* ``list_meeting_transcripts``
* ``create_dummy_dataset``

Run it with:

.. code-block:: bash

   ODOO_URL=http://localhost:8069 \
   ODOO_DB=<db> \
   ODOO_USERNAME=<user> \
   ODOO_PASSWORD=<password> \
   python3 addons/crm_ai_team/tools/mcp_server.py

Agent runtime and observability
------------------------------

This module also includes a built-in orchestration and observability layer:

* **Team runtime**: each team can run an orchestration pipeline on pending conversation summaries.
* **Rule-based agents**: specialized team members evaluate summary sentiment and themes to create relationship signals (cross-sell, upsell, renewal, churn risk).
* **Run telemetry**: each pipeline execution writes a run record and detailed run logs.
* **Operational dashboards**: Odoo views for runs/logs (tree, graph, pivot) provide performance and error visibility directly in CRM.

Automatic meeting transcript capture
-----------------------------------

The module supports ingesting transcripts from common providers:

* Zoom
* Microsoft Teams
* Google Meet
* Other sources

Imported transcripts can be auto-processed into ``crm.ai.conversation.summary`` records,
with inferred sentiment and themes, then routed into the team runtime for downstream action.

Programmatic dummy data generation
----------------------------------

For test automation and demos, ``crm.ai.agent.team`` exposes
``create_dummy_dataset`` to generate teams, agents, opportunities,
transcripts, summaries, and optional run telemetry in one call.

The same capability is exposed in MCP via ``create_dummy_dataset``.

Repeatable deployment
---------------------

A production-style repeatable deployment package is provided in
``addons/crm_ai_team/deploy`` with:

* a Docker image definition bundling this module and MCP dependency
* a Compose stack for Postgres + Odoo init/runtime + MCP server
* environment template and deployment helper script

See ``addons/crm_ai_team/deploy/README.md`` for operational instructions.
For Windows-specific local startup/testing commands, see ``addons/crm_ai_team/LOCAL_TESTING.md``.

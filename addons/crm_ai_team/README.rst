CRM AI Agent Team
=================

This module provides an architecture foundation for managing customer relationships with an AI agent team.

**Version 2.0** - Now with LLM configuration, vector embeddings, and CRM decoupling!

Core building blocks
--------------------

* **AI Agent Team**: groups specialized agents with configurable LLM providers (OpenAI, Anthropic, Google AI, Azure, local).
* **AI Agent**: stores role, instruction/prompt, LLM overrides, and tool definitions.
* **Conversation Summary**: captures customer interaction summaries with sentiment, themes, and vector embeddings.
* **Conversation Theme**: classifies reusable themes such as cross-sell, upsell, renewal, and churn risk.
* **Relationship Signal**: tracks structured recommendations with full lifecycle management (new → acknowledged → in_progress → resolved).
* **Signal Rule**: configurable rules for signal generation (replaces hardcoded logic).

Linkage to business records
---------------------------

Conversation summaries and relationship signals can be linked to:

* Sales opportunities via Reference fields (works with CRM or other sales modules)
* Reference cases/tickets via a dynamic reference field (`helpdesk.ticket`, `project.task`, or `crm.lead` when available)

This allows AI output to flow into both sales and case-management workflows.

**Plug-and-Play**: Works without CRM module installed - optional integration when CRM is available.

MCP server
----------

The module includes an enhanced MCP server implementation at
``addons/crm_ai_team/tools/mcp_server.py`` with pagination, error handling,
resources, and prompts.

**Features:**

* **Pagination**: All list tools support `limit` and `offset` with total counts
* **Error handling**: Sanitized errors safe for AI agent consumption
* **Resources**: Model discovery, health checks, field introspection
* **Prompts**: Pre-built templates for common AI tasks

**Exposed tools:**

* ``list_conversation_summaries`` - Paginated listing
* ``create_conversation_summary`` - Create with LLM metadata
* ``create_relationship_signal`` - Create with lifecycle state
* ``list_sales_opportunities`` - CRM-optional listing
* ``run_agent_team`` - Execute pipeline
* ``get_observability_snapshot`` - Metrics and latest runs
* ``ingest_meeting_transcript`` - Import from meeting providers
* ``list_meeting_transcripts`` - Paginated listing
* ``create_dummy_dataset`` - Generate demo data
* ``list_signal_rules`` - List configurable rules
* ``get_agent_team_config`` - Get LLM configuration
* ``get_agent_config`` - Get agent settings

**Exposed resources:**

* ``odoo://health`` - Health and connection status
* ``odoo://models`` - List all AI CRM models
* ``odoo://{model}/fields`` - Field definitions
* ``odoo://{model}/record/{id}`` - Read specific record
* ``odoo://signal-types`` - Available signal types
* ``odoo://sentiment-options`` - Sentiment classifications

**Exposed prompts:**

* ``analyze_customer_relationship`` - Analyze from summary
* ``configure_agent_team`` - Configure LLM settings

Run it with:

.. code-block:: bash

   ODOO_URL=http://localhost:8069 \\
   ODOO_DB=<db> \\
   ODOO_USERNAME=<user> \\
   ODOO_PASSWORD=<password> \\
   python3 addons/crm_ai_team/tools/mcp_server.py

See ``MCP_SERVER_DOCUMENTATION.md`` for complete API documentation.

Agent runtime and observability
------------------------------

This module includes a built-in orchestration and observability layer:

* **Team runtime**: each team can run an orchestration pipeline on pending conversation summaries.
* **Rule-based agents**: configurable signal rules evaluate summary sentiment and themes.
* **LLM configuration**: teams and agents can configure LLM providers, models, and prompts.
* **Vector embeddings**: summaries support embedding storage for semantic search.
* **Run telemetry**: each pipeline execution writes a run record and detailed run logs.
* **Signal lifecycle**: full state management (new → acknowledged → in_progress → resolved).
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

"""MCP server for CRM AI Team.

Run with environment variables:
- ODOO_URL (default: http://localhost:8069)
- ODOO_DB
- ODOO_USERNAME
- ODOO_PASSWORD

Example:
    ODOO_DB=mydb ODOO_USERNAME=admin ODOO_PASSWORD=admin \
    python3 addons/crm_ai_team/tools/mcp_server.py
"""

import os
import xmlrpc.client
from typing import Any

from mcp.server.fastmcp import FastMCP


class OdooClient:
    def __init__(self) -> None:
        self.url = os.getenv('ODOO_URL', 'http://localhost:8069').rstrip('/')
        self.db = os.environ['ODOO_DB']
        self.username = os.environ['ODOO_USERNAME']
        self.password = os.environ['ODOO_PASSWORD']

        common_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.uid = common_proxy.authenticate(self.db, self.username, self.password, {})
        if not self.uid:
            raise ValueError('Failed to authenticate to Odoo. Check ODOO_* credentials.')
        self.model_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')

    def execute_kw(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        return self.model_proxy.execute_kw(
            self.db,
            self.uid,
            self.password,
            model,
            method,
            args,
            kwargs or {},
        )


mcp = FastMCP('crm-ai-team')


def _client() -> OdooClient:
    return OdooClient()


@mcp.tool()
def list_conversation_summaries(limit: int = 20) -> list[dict[str, Any]]:
    """List recent AI conversation summaries."""
    client = _client()
    ids = client.execute_kw(
        'crm.ai.conversation.summary',
        'search',
        [[]],
        {'limit': max(1, min(limit, 100)), 'order': 'conversation_datetime desc, id desc'},
    )
    return client.execute_kw(
        'crm.ai.conversation.summary',
        'read',
        [ids],
        {'fields': ['name', 'conversation_datetime', 'sentiment', 'partner_id', 'opportunity_id']},
    )


@mcp.tool()
def create_conversation_summary(
    title: str,
    summary: str,
    sentiment: str = 'neutral',
    partner_id: int | None = None,
    team_id: int | None = None,
    agent_id: int | None = None,
    opportunity_id: int | None = None,
    key_points: str | None = None,
) -> dict[str, Any]:
    """Create a crm.ai.conversation.summary record."""
    client = _client()
    values: dict[str, Any] = {
        'name': title,
        'summary': summary,
        'sentiment': sentiment,
    }
    if partner_id:
        values['partner_id'] = partner_id
    if team_id:
        values['team_id'] = team_id
    if agent_id:
        values['agent_id'] = agent_id
    if opportunity_id:
        values['opportunity_id'] = opportunity_id
    if key_points:
        values['key_points'] = key_points

    summary_id = client.execute_kw('crm.ai.conversation.summary', 'create', [values])
    record = client.execute_kw(
        'crm.ai.conversation.summary',
        'read',
        [[summary_id]],
        {'fields': ['name', 'conversation_datetime', 'sentiment', 'partner_id', 'opportunity_id']},
    )
    return {'id': summary_id, 'record': record[0]}


@mcp.tool()
def create_relationship_signal(
    summary_id: int,
    signal_type: str,
    recommendation: str,
    priority: str = 'medium',
    confidence: float = 0.5,
    lead_id: int | None = None,
    owner_id: int | None = None,
) -> dict[str, Any]:
    """Create a crm.ai.relationship.signal for cross-sell/upsell/renewal/churn workflows."""
    client = _client()
    values: dict[str, Any] = {
        'summary_id': summary_id,
        'signal_type': signal_type,
        'recommendation': recommendation,
        'priority': priority,
        'confidence': confidence,
    }
    if lead_id:
        values['lead_id'] = lead_id
    if owner_id:
        values['owner_id'] = owner_id

    signal_id = client.execute_kw('crm.ai.relationship.signal', 'create', [values])
    record = client.execute_kw(
        'crm.ai.relationship.signal',
        'read',
        [[signal_id]],
        {'fields': ['summary_id', 'signal_type', 'priority', 'confidence', 'lead_id', 'owner_id']},
    )
    return {'id': signal_id, 'record': record[0]}


@mcp.tool()
def list_sales_opportunities(partner_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """List CRM opportunities that can be linked from AI outputs."""
    client = _client()
    domain: list[Any] = [('type', '=', 'opportunity')]
    if partner_id:
        domain.append(('partner_id', '=', partner_id))

    ids = client.execute_kw(
        'crm.lead',
        'search',
        [domain],
        {'limit': max(1, min(limit, 100)), 'order': 'priority desc, create_date desc'},
    )
    return client.execute_kw(
        'crm.lead',
        'read',
        [ids],
        {'fields': ['name', 'partner_id', 'stage_id', 'probability', 'expected_revenue']},
    )


@mcp.tool()
def run_agent_team(team_id: int) -> dict[str, Any]:
    """Execute the team orchestration pipeline on pending summaries."""
    client = _client()
    client.execute_kw('crm.ai.agent.team', 'action_run_agent_team', [[team_id]])
    run_ids = client.execute_kw(
        'crm.ai.agent.run',
        'search',
        [[('team_id', '=', team_id)]],
        {'limit': 1, 'order': 'start_datetime desc, id desc'},
    )
    if not run_ids:
        return {'team_id': team_id, 'status': 'no_run'}
    run_record = client.execute_kw(
        'crm.ai.agent.run',
        'read',
        [run_ids],
        {
            'fields': [
                'name',
                'team_id',
                'status',
                'start_datetime',
                'end_datetime',
                'processed_summary_count',
                'success_step_count',
                'failed_step_count',
                'duration_seconds',
            ]
        },
    )[0]
    return {'team_id': team_id, 'run': run_record}


@mcp.tool()
def get_observability_snapshot(team_id: int | None = None) -> dict[str, Any]:
    """Return observability metrics from crm.ai.agent.run and crm.ai.agent.run.log."""
    client = _client()
    run_domain: list[Any] = []
    log_domain: list[Any] = []
    if team_id:
        run_domain.append(('team_id', '=', team_id))
        log_domain.append(('team_id', '=', team_id))

    run_count = client.execute_kw('crm.ai.agent.run', 'search_count', [run_domain])
    failed_run_count = client.execute_kw(
        'crm.ai.agent.run',
        'search_count',
        [[*run_domain, ('status', '=', 'failed')]],
    )
    partial_run_count = client.execute_kw(
        'crm.ai.agent.run',
        'search_count',
        [[*run_domain, ('status', '=', 'partial')]],
    )
    log_error_count = client.execute_kw(
        'crm.ai.agent.run.log',
        'search_count',
        [[*log_domain, ('log_level', '=', 'error')]],
    )

    latest_run_ids = client.execute_kw(
        'crm.ai.agent.run',
        'search',
        [run_domain],
        {'limit': 5, 'order': 'start_datetime desc, id desc'},
    )
    latest_runs = client.execute_kw(
        'crm.ai.agent.run',
        'read',
        [latest_run_ids],
        {'fields': ['name', 'team_id', 'status', 'processed_summary_count', 'failed_step_count']},
    )

    return {
        'team_id': team_id,
        'run_count': run_count,
        'failed_run_count': failed_run_count,
        'partial_run_count': partial_run_count,
        'error_log_count': log_error_count,
        'latest_runs': latest_runs,
    }


@mcp.tool()
def ingest_meeting_transcript(
    title: str,
    provider: str,
    transcript_text: str,
    external_ref: str | None = None,
    partner_id: int | None = None,
    team_id: int | None = None,
    opportunity_id: int | None = None,
    language: str = 'en',
    auto_process: bool = True,
) -> dict[str, Any]:
    """Ingest a Zoom/Teams/Meet transcript and optionally auto-process it to a summary."""
    client = _client()
    values: dict[str, Any] = {
        'name': title,
        'provider': provider,
        'raw_transcript': transcript_text,
        'language': language,
    }
    if external_ref:
        values['external_ref'] = external_ref
    if partner_id:
        values['partner_id'] = partner_id
    if team_id:
        values['team_id'] = team_id
    if opportunity_id:
        values['opportunity_id'] = opportunity_id

    transcript_id = client.execute_kw('crm.ai.meeting.transcript', 'create', [values])
    if auto_process:
        client.execute_kw('crm.ai.meeting.transcript', 'action_process_transcript', [[transcript_id]])
    transcript = client.execute_kw(
        'crm.ai.meeting.transcript',
        'read',
        [[transcript_id]],
        {'fields': ['name', 'provider', 'external_ref', 'ingest_status', 'summary_id', 'processing_error']},
    )[0]
    return {'id': transcript_id, 'record': transcript}


@mcp.tool()
def list_meeting_transcripts(
    provider: str | None = None,
    ingest_status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List imported transcripts from Zoom/Teams/Meet/other providers."""
    client = _client()
    domain: list[Any] = []
    if provider:
        domain.append(('provider', '=', provider))
    if ingest_status:
        domain.append(('ingest_status', '=', ingest_status))
    ids = client.execute_kw(
        'crm.ai.meeting.transcript',
        'search',
        [domain],
        {'limit': max(1, min(limit, 100)), 'order': 'meeting_datetime desc, id desc'},
    )
    return client.execute_kw(
        'crm.ai.meeting.transcript',
        'read',
        [ids],
        {'fields': ['name', 'meeting_datetime', 'provider', 'external_ref', 'ingest_status', 'summary_id']},
    )


@mcp.tool()
def create_dummy_dataset(
    team_name: str = 'AI Demo Team',
    agent_count: int = 5,
    transcript_count: int = 20,
    auto_run: bool = True,
) -> dict[str, Any]:
    """Create programmatic dummy records for demos/load testing of agent loops."""
    client = _client()
    return client.execute_kw(
        'crm.ai.agent.team',
        'create_dummy_dataset',
        [],
        {
            'team_name': team_name,
            'agent_count': max(1, min(agent_count, 25)),
            'transcript_count': max(1, min(transcript_count, 200)),
            'auto_run': auto_run,
        },
    )


if __name__ == '__main__':
    mcp.run()

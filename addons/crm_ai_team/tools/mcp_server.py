"""MCP server for CRM AI Team.

Run with environment variables:
- ODOO_URL (default: http://localhost:8069)
- ODOO_DB
- ODOO_USERNAME
- ODOO_PASSWORD

Example:
ODOO_DB=mydb ODOO_USERNAME=admin ODOO_PASSWORD=admin \\
python3 addons/crm_ai_team/tools/mcp_server.py
"""

import json
import os
import xmlrpc.client
from typing import Any

from mcp.server.fastmcp import FastMCP


class OdooError(Exception):
    """Base exception for Odoo-related errors."""

    pass


class AuthenticationError(OdooError):
    """Authentication failed."""

    pass


class NotFoundError(OdooError):
    """Record not found."""

    pass


class ValidationError(OdooError):
    """Validation error from Odoo."""

    pass


class ErrorSanitizer:
    """Sanitize Odoo errors for safe exposure to AI agents."""

    SENSITIVE_PATTERNS = [
        ('password', '[REDACTED]'),
        ('secret', '[REDACTED]'),
        ('token', '[REDACTED]'),
        ('key', '[REDACTED]'),
        ('Access Error', 'Permission denied'),
        ('does not exist', 'Record not found'),
        ('MissingError', 'Record not found'),
    ]

    @classmethod
    def sanitize(cls, error_message: str) -> str:
        """Sanitize error message for safe exposure."""
        sanitized = error_message
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            if pattern.lower() in sanitized.lower():
                sanitized = sanitized.replace(pattern, replacement)
        return sanitized


class OdooClient:
    """XML-RPC client for Odoo with error handling and pagination support."""

    def __init__(self) -> None:
        self.url = os.getenv('ODOO_URL', 'http://localhost:8069').rstrip('/')
        self.db = os.environ['ODOO_DB']
        self.username = os.environ['ODOO_USERNAME']
        self.password = os.environ['ODOO_PASSWORD']

        try:
            common_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common_proxy.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                raise AuthenticationError('Failed to authenticate to Odoo. Check ODOO_* credentials.')
            self.model_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        except xmlrpc.client.Fault as e:
            raise AuthenticationError(ErrorSanitizer.sanitize(e.faultString))
        except ConnectionError as e:
            raise OdooError(f'Cannot connect to Odoo at {self.url}: {str(e)}')

    def execute_kw(
        self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None
    ) -> Any:
        """Execute XML-RPC call with error handling."""
        try:
            result = self.model_proxy.execute_kw(
                self.db,
                self.uid,
                self.password,
                model,
                method,
                args,
                kwargs or {},
            )
            return result
        except xmlrpc.client.Fault as e:
            error_msg = ErrorSanitizer.sanitize(e.faultString)
            if 'Access Error' in error_msg or 'AccessDenied' in error_msg:
                raise ValidationError(f'Permission denied: {error_msg}')
            if 'does not exist' in error_msg or 'MissingError' in error_msg:
                raise NotFoundError(error_msg)
            raise ValidationError(error_msg)
        except Exception as e:
            raise OdooError(f'Odoo operation failed: {str(e)}')

    def search_read(
        self,
        model: str,
        domain: list[Any],
        fields: list[str],
        limit: int = 20,
        offset: int = 0,
        order: str | None = None,
    ) -> dict[str, Any]:
        """Paginated search and read with total count."""
        total = self.execute_kw(model, 'search_count', [domain])
        records = self.execute_kw(
            model,
            'search_read',
            [domain],
            {'fields': fields, 'limit': limit, 'offset': offset, 'order': order or 'id desc'},
        )
        return {
            'records': records,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total,
        }


# Initialize MCP server with pagination
mcp = FastMCP('crm-ai-team')


def _client() -> OdooClient:
    return OdooClient()


# =============================================================================
# TOOLS
# =============================================================================


@mcp.tool()
def list_conversation_summaries(
    limit: int = 20, offset: int = 0, team_id: int | None = None, sentiment: str | None = None
) -> dict[str, Any]:
    """List AI conversation summaries with pagination.

    Args:
        limit: Maximum records to return (1-100, default 20)
        offset: Number of records to skip (default 0)
        team_id: Filter by team ID (optional)
        sentiment: Filter by sentiment (optional)

    Returns:
        Paginated result with records, total, and has_more flag.
    """
    client = _client()
    domain: list[Any] = []
    if team_id:
        domain.append(('team_id', '=', team_id))
    if sentiment:
        domain.append(('sentiment', '=', sentiment))

    return client.search_read(
        'crm.ai.conversation.summary',
        domain,
        ['name', 'conversation_datetime', 'sentiment', 'partner_id', 'opportunity_ref', 'processed'],
        limit=max(1, min(limit, 100)),
        offset=max(0, offset),
        order='conversation_datetime desc, id desc',
    )


@mcp.tool()
def create_conversation_summary(
    title: str,
    summary: str,
    sentiment: str = 'neutral',
    partner_id: int | None = None,
    team_id: int | None = None,
    agent_id: int | None = None,
    opportunity_ref: str | None = None,
    key_points: str | None = None,
) -> dict[str, Any]:
    """Create a crm.ai.conversation.summary record.

    Args:
        title: Summary title
        summary: Conversation summary text
        sentiment: Sentiment classification (very_negative, negative, neutral, positive, very_positive)
        partner_id: Customer partner ID (optional)
        team_id: AI agent team ID (optional)
        agent_id: Primary agent ID (optional)
        opportunity_ref: Opportunity reference in format 'model,id' (e.g., 'crm.lead,42')
        key_points: Structured key takeaways (optional)

    Returns:
        Created record with ID and details.
    """
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
    if opportunity_ref:
        values['opportunity_ref'] = opportunity_ref
    if key_points:
        values['key_points'] = key_points

    summary_id = client.execute_kw('crm.ai.conversation.summary', 'create', [values])
    record = client.execute_kw(
        'crm.ai.conversation.summary',
        'read',
        [[summary_id]],
        {'fields': ['name', 'conversation_datetime', 'sentiment', 'partner_id', 'opportunity_ref']},
    )
    return {'id': summary_id, 'record': record[0]}


@mcp.tool()
def create_relationship_signal(
    summary_id: int,
    signal_type: str,
    recommendation: str,
    priority: str = 'medium',
    confidence: float = 0.5,
    lead_ref: str | None = None,
    owner_id: int | None = None,
) -> dict[str, Any]:
    """Create a crm.ai.relationship.signal for cross-sell/upsell/renewal/churn workflows.

    Args:
        summary_id: Parent conversation summary ID
        signal_type: Signal type (cross_sell, upsell, renewal, churn_risk)
        recommendation: Actionable recommendation text
        priority: Priority level (low, medium, high)
        confidence: Confidence score (0.0-1.0)
        lead_ref: Opportunity reference in format 'model,id' (optional)
        owner_id: Assigned owner user ID (optional)

    Returns:
        Created signal record.
    """
    client = _client()
    values: dict[str, Any] = {
        'summary_id': summary_id,
        'signal_type': signal_type,
        'recommendation': recommendation,
        'priority': priority,
        'confidence': confidence,
    }
    if lead_ref:
        values['lead_ref'] = lead_ref
    if owner_id:
        values['owner_id'] = owner_id

    signal_id = client.execute_kw('crm.ai.relationship.signal', 'create', [values])
    record = client.execute_kw(
        'crm.ai.relationship.signal',
        'read',
        [[signal_id]],
        {'fields': ['summary_id', 'signal_type', 'priority', 'confidence', 'lead_ref', 'owner_id', 'state']},
    )
    return {'id': signal_id, 'record': record[0]}


@mcp.tool()
def list_sales_opportunities(
    partner_id: int | None = None, limit: int = 20, offset: int = 0
) -> dict[str, Any]:
    """List CRM opportunities that can be linked from AI outputs.

    This tool only works if CRM module (crm.lead) is installed.

    Args:
        partner_id: Filter by customer partner ID (optional)
        limit: Maximum records to return (1-100)
        offset: Number of records to skip

    Returns:
        Paginated result with opportunity records.
    """
    client = _client()
    domain: list[Any] = [('type', '=', 'opportunity')]
    if partner_id:
        domain.append(('partner_id', '=', partner_id))

    # Check if crm.lead exists
    try:
        return client.search_read(
            'crm.lead',
            domain,
            ['name', 'partner_id', 'stage_id', 'probability', 'expected_revenue'],
            limit=max(1, min(limit, 100)),
            offset=max(0, offset),
            order='priority desc, create_date desc',
        )
    except NotFoundError:
        return {'records': [], 'total': 0, 'error': 'CRM module not installed or no access'}


@mcp.tool()
def run_agent_team(team_id: int) -> dict[str, Any]:
    """Execute the team orchestration pipeline on pending summaries.

    Args:
        team_id: AI agent team ID to run

    Returns:
        Execution result with run details.
    """
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
    """Return observability metrics from crm.ai.agent.run and crm.ai.agent.run.log.

    Args:
        team_id: Filter by specific team (optional, all teams if None)

    Returns:
        Aggregated metrics and recent runs.
    """
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
    opportunity_ref: str | None = None,
    language: str = 'en',
    auto_process: bool = True,
) -> dict[str, Any]:
    """Ingest a Zoom/Teams/Meet transcript and optionally auto-process it to a summary.

    Args:
        title: Meeting title
        provider: Source provider (zoom, microsoft_teams, google_meet, other)
        transcript_text: Raw transcript content
        external_ref: Provider's meeting identifier (optional)
        partner_id: Customer partner ID (optional)
        team_id: AI agent team ID (optional)
        opportunity_ref: Opportunity reference in format 'model,id' (optional)
        language: Language code (default: en)
        auto_process: Automatically process to summary (default: True)

    Returns:
        Created transcript record with processing status.
    """
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
    if opportunity_ref:
        values['opportunity_ref'] = opportunity_ref

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
    offset: int = 0,
) -> dict[str, Any]:
    """List imported transcripts from Zoom/Teams/Meet/other providers.

    Args:
        provider: Filter by provider (zoom, microsoft_teams, google_meet, other)
        ingest_status: Filter by status (new, processed, failed)
        limit: Maximum records to return (1-100)
        offset: Number of records to skip

    Returns:
        Paginated result with transcript records.
    """
    client = _client()
    domain: list[Any] = []
    if provider:
        domain.append(('provider', '=', provider))
    if ingest_status:
        domain.append(('ingest_status', '=', ingest_status))

    return client.search_read(
        'crm.ai.meeting.transcript',
        domain,
        ['name', 'meeting_datetime', 'provider', 'external_ref', 'ingest_status', 'summary_id'],
        limit=max(1, min(limit, 100)),
        offset=max(0, offset),
        order='meeting_datetime desc, id desc',
    )


@mcp.tool()
def create_dummy_dataset(
    team_name: str = 'AI Demo Team',
    agent_count: int = 5,
    transcript_count: int = 20,
    auto_run: bool = True,
) -> dict[str, Any]:
    """Create programmatic dummy records for demos/load testing of agent loops.

    Args:
        team_name: Name for the demo team
        agent_count: Number of agents to create (1-25)
        transcript_count: Number of transcripts to create (1-200)
        auto_run: Automatically execute team pipeline (default: True)

    Returns:
        Summary of created records.
    """
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


@mcp.tool()
def list_signal_rules(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """List configurable signal generation rules.

    Args:
        limit: Maximum records to return (1-100)
        offset: Number of records to skip

    Returns:
        Paginated result with signal rules.
    """
    client = _client()
    return client.search_read(
        'crm.ai.signal.rule',
        [('active', '=', True)],
        ['name', 'sequence', 'condition_sentiment', 'condition_agent_role', 'action_signal_type', 'action_priority'],
        limit=max(1, min(limit, 100)),
        offset=max(0, offset),
        order='sequence, id',
    )


@mcp.tool()
def get_agent_team_config(team_id: int) -> dict[str, Any]:
    """Get LLM configuration for a specific agent team.

    Args:
        team_id: Team ID

    Returns:
        Team configuration including LLM settings.
    """
    client = _client()
    record = client.execute_kw(
        'crm.ai.agent.team',
        'read',
        [[team_id]],
        {
            'fields': [
                'name',
                'llm_provider',
                'llm_model',
                'llm_api_endpoint',
                'llm_temperature',
                'llm_max_tokens',
                'llm_system_prompt',
                'active',
            ]
        },
    )
    if not record:
        raise NotFoundError(f'Team {team_id} not found')
    return {'team_id': team_id, 'config': record[0]}


@mcp.tool()
def get_agent_config(agent_id: int) -> dict[str, Any]:
    """Get LLM configuration for a specific agent.

    Args:
        agent_id: Agent ID

    Returns:
        Agent configuration including LLM settings and prompts.
    """
    client = _client()
    record = client.execute_kw(
        'crm.ai.agent',
        'read',
        [[agent_id]],
        {
            'fields': [
                'name',
                'role',
                'team_id',
                'llm_provider',
                'llm_model',
                'llm_temperature',
                'llm_max_tokens',
                'system_prompt',
                'response_format',
                'instruction',
                'active',
            ]
        },
    )
    if not record:
        raise NotFoundError(f'Agent {agent_id} not found')
    return {'agent_id': agent_id, 'config': record[0]}


# =============================================================================
# RESOURCES
# =============================================================================


@mcp.resource('odoo://health')
def health_check() -> str:
    """Health and connection status check.

    Returns connection status and basic statistics.
    """
    try:
        client = _client()
        team_count = client.execute_kw('crm.ai.agent.team', 'search_count', [[]])
        agent_count = client.execute_kw('crm.ai.agent', 'search_count', [[]])
        summary_count = client.execute_kw('crm.ai.conversation.summary', 'search_count', [[]])

        return json.dumps(
            {
                'status': 'healthy',
                'connected': True,
                'url': client.url,
                'database': client.db,
                'user_id': client.uid,
                'statistics': {
                    'teams': team_count,
                    'agents': agent_count,
                    'summaries': summary_count,
                },
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({'status': 'unhealthy', 'error': str(e)}, indent=2)


@mcp.resource('odoo://models')
def list_available_models() -> str:
    """List all AI CRM models with their fields.

    Returns a description of all models in the AI CRM system.
    """
    models_info = {
        'crm.ai.agent.team': {
            'name': 'AI Agent Team',
            'description': 'Team configuration with LLM provider settings',
            'key_fields': ['name', 'llm_provider', 'llm_model', 'llm_temperature', 'llm_max_tokens'],
        },
        'crm.ai.agent': {
            'name': 'AI Agent',
            'description': 'Agent profile with role and LLM overrides',
            'key_fields': ['name', 'role', 'team_id', 'system_prompt', 'response_format'],
        },
        'crm.ai.theme': {
            'name': 'Conversation Theme',
            'description': 'Theme classification for conversations',
            'key_fields': ['name', 'code', 'priority_weight'],
        },
        'crm.ai.conversation.summary': {
            'name': 'Conversation Summary',
            'description': 'AI-processed conversation with embeddings',
            'key_fields': ['name', 'sentiment', 'summary', 'theme_ids', 'embedding_vector'],
        },
        'crm.ai.meeting.transcript': {
            'name': 'Meeting Transcript',
            'description': 'Imported transcript from meeting providers',
            'key_fields': ['name', 'provider', 'raw_transcript', 'ingest_status'],
        },
        'crm.ai.relationship.signal': {
            'name': 'Relationship Signal',
            'description': 'Actionable signal from AI analysis',
            'key_fields': ['signal_type', 'priority', 'confidence', 'recommendation', 'state'],
        },
        'crm.ai.signal.rule': {
            'name': 'Signal Rule',
            'description': 'Configurable rule for signal generation',
            'key_fields': ['name', 'sequence', 'condition_sentiment', 'action_signal_type'],
        },
        'crm.ai.agent.run': {
            'name': 'Agent Run',
            'description': 'Pipeline execution record with observability',
            'key_fields': ['name', 'team_id', 'status', 'processed_summary_count'],
        },
        'crm.ai.agent.run.log': {
            'name': 'Run Log',
            'description': 'Detailed execution log entries',
            'key_fields': ['run_id', 'agent_id', 'log_level', 'message'],
        },
    }
    return json.dumps(models_info, indent=2)


@mcp.resource('odoo://{model}/fields')
def get_model_fields(model: str) -> str:
    """Get field definitions for a specific model.

    Args:
        model: Model name (e.g., crm.ai.agent.team)

    Returns:
        Field definitions for the model.
    """
    valid_models = [
        'crm.ai.agent.team',
        'crm.ai.agent',
        'crm.ai.theme',
        'crm.ai.conversation.summary',
        'crm.ai.meeting.transcript',
        'crm.ai.relationship.signal',
        'crm.ai.signal.rule',
        'crm.ai.agent.run',
        'crm.ai.agent.run.log',
    ]

    if model not in valid_models:
        return json.dumps({'error': f'Invalid model: {model}', 'valid_models': valid_models}, indent=2)

    client = _client()
    try:
        fields_info = client.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'required']})
        return json.dumps(fields_info, indent=2)
    except Exception as e:
        return json.dumps({'error': str(e)}, indent=2)


@mcp.resource('odoo://{model}/record/{id}')
def get_record(model: str, id: int) -> str:
    """Read a specific record from a model.

    Args:
        model: Model name (e.g., crm.ai.conversation.summary)
        id: Record ID

    Returns:
        Record data as JSON.
    """
    valid_models = [
        'crm.ai.agent.team',
        'crm.ai.agent',
        'crm.ai.theme',
        'crm.ai.conversation.summary',
        'crm.ai.meeting.transcript',
        'crm.ai.relationship.signal',
        'crm.ai.signal.rule',
        'crm.ai.agent.run',
        'crm.ai.agent.run.log',
    ]

    if model not in valid_models:
        return json.dumps({'error': f'Invalid model: {model}', 'valid_models': valid_models}, indent=2)

    client = _client()
    try:
        records = client.execute_kw(model, 'read', [[id]])
        if not records:
            return json.dumps({'error': f'Record {id} not found in {model}'}, indent=2)
        return json.dumps(records[0], indent=2, default=str)
    except Exception as e:
        return json.dumps({'error': str(e)}, indent=2)


@mcp.resource('odoo://signal-types')
def get_signal_types() -> str:
    """Get available signal types with descriptions.

    Returns all signal type options for relationship signals.
    """
    signal_types = [
        {'code': 'cross_sell', 'name': 'Cross-sell Opportunity', 'description': 'Opportunity to sell complementary products'},
        {'code': 'upsell', 'name': 'Upsell Opportunity', 'description': 'Opportunity to upgrade existing purchase'},
        {'code': 'renewal', 'name': 'Renewal Action', 'description': 'Contract or subscription renewal needed'},
        {'code': 'churn_risk', 'name': 'Churn Risk', 'description': 'Customer at risk of leaving'},
    ]
    return json.dumps(signal_types, indent=2)


@mcp.resource('odoo://sentiment-options')
def get_sentiment_options() -> str:
    """Get available sentiment classifications.

    Returns all sentiment type options for conversation summaries.
    """
    sentiments = [
        {'code': 'very_negative', 'name': 'Very Negative', 'score': -2},
        {'code': 'negative', 'name': 'Negative', 'score': -1},
        {'code': 'neutral', 'name': 'Neutral', 'score': 0},
        {'code': 'positive', 'name': 'Positive', 'score': 1},
        {'code': 'very_positive', 'name': 'Very Positive', 'score': 2},
    ]
    return json.dumps(sentiments, indent=2)


# =============================================================================
# PROMPTS
# =============================================================================


@mcp.prompt()
def analyze_customer_relationship(summary_id: int) -> str:
    """Prompt template for analyzing customer relationship from a summary.

    Args:
        summary_id: The conversation summary ID to analyze

    Returns:
        Prompt for analyzing the customer relationship.
    """
    return f"""Analyze the customer relationship based on conversation summary ID {summary_id}.

1. First, use the get_record resource: odoo://crm.ai.conversation.summary/record/{summary_id}
2. Then, use list_relationship_signals with summary_id={summary_id} to see existing signals
3. Analyze the sentiment, themes, and key points
4. Determine if a new relationship signal should be created

Consider:
- Cross-sell opportunities (adjacent products)
- Upsell opportunities (upgrades)
- Renewal timing and needs
- Churn risk indicators

Provide your analysis and recommendation."""


@mcp.prompt()
def configure_agent_team(team_id: int) -> str:
    """Prompt template for configuring an agent team's LLM settings.

    Args:
        team_id: The team ID to configure

    Returns:
        Prompt for configuring the team.
    """
    return f"""Configure the LLM settings for agent team ID {team_id}.

1. First, use get_agent_team_config(team_id={team_id}) to see current settings
2. Use list_signal_rules() to see active signal rules
3. Review the current configuration and suggest improvements

Consider:
- LLM provider selection (openai, anthropic, google, local)
- Model selection based on use case
- Temperature settings for creativity vs consistency
- System prompt for team-wide behavior
- Response format preferences

Provide configuration recommendations."""


if __name__ == '__main__':
    mcp.run()

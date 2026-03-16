"""
CRM AI Team - Extended Features Module

This module extends crm_ai_team with:
1. Natural Language Query Interface - Ask questions in plain English
2. Email Intelligence - Analyze emails for sentiment, action items, signals
3. Customer Health Scoring - Track customer health and churn risk
4. Enhanced Observability - Detailed run viewer with step-by-step logs
5. Human-in-the-Loop - Approval workflow for high-stakes actions
"""

from datetime import datetime, timedelta
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


# =============================================================================
# NATURAL LANGUAGE QUERY INTERFACE
# =============================================================================

class CrmAiNlQuery(models.Model):
    """Natural Language Query - Ask questions about CRM data in plain English.

    This model stores queries from users and their AI-generated responses,
    including the reasoning chain and any actions taken.
    """
    _name = 'crm.ai.nl.query'
    _description = 'Natural Language Query'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Query',
        required=True,
        tracking=True,
        help='The natural language question asked by the user.',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Asked By',
        default=lambda self: self.env.user.id,
        tracking=True,
    )
    team_id = fields.Many2one(
        'crm.ai.agent.team',
        string='Team',
        tracking=True,
        help='Team that processed this query.',
    )

    # Response
    response = fields.Text(
        string='AI Response',
        tracking=True,
        help='The AI-generated response to the query.',
    )
    response_format = fields.Selection(
        [('text', 'Text'), ('json', 'JSON'), ('markdown', 'Markdown')],
        default='markdown',
        string='Response Format',
    )

    # Execution details
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('requires_approval', 'Requires Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )

    # Reasoning chain (JSON array of steps)
    reasoning_chain = fields.Text(
        string='Reasoning Chain',
        help='JSON array of reasoning steps taken to answer the query.',
    )

    # Actions taken (JSON array)
    actions_taken = fields.Text(
        string='Actions Taken',
        help='JSON array of actions performed (e.g., records created, updated).',
    )

    # Token usage
    input_tokens = fields.Integer(string='Input Tokens')
    output_tokens = fields.Integer(string='Output Tokens')
    total_cost = fields.Float(string='Estimated Cost (USD)')

    # Processing time
    processing_started = fields.Datetime(string='Processing Started')
    processing_completed = fields.Datetime(string='Processing Completed')
    processing_duration_ms = fields.Integer(
        string='Processing Duration (ms)',
        compute='_compute_processing_duration',
        store=True,
    )

    # Error handling
    error_message = fields.Text(string='Error Message')
    retry_count = fields.Integer(default=0, string='Retry Count')

    # Linked records
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Customer',
        tracking=True,
    )
    opportunity_ref = fields.Reference(
        selection='_get_referenceable_models',
        string='Related Opportunity',
    )
    summary_id = fields.Many2one(
        'crm.ai.conversation.summary',
        string='Related Summary',
    )

    @api.model
    def _get_referenceable_models(self):
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    @api.depends('processing_started', 'processing_completed')
    def _compute_processing_duration(self):
        for record in self:
            if record.processing_started and record.processing_completed:
                delta = record.processing_completed - record.processing_started
                record.processing_duration_ms = int(delta.total_seconds() * 1000)
            else:
                record.processing_duration_ms = 0

    def action_submit(self):
        """Submit the query for processing."""
        self.write({'state': 'processing', 'processing_started': fields.Datetime.now()})
        # Actual processing would be done by an external AI service
        return True

    def action_approve(self):
        """Approve a query that requires human approval."""
        self.write({'state': 'approved'})
        return True

    def action_reject(self):
        """Reject a query that requires human approval."""
        self.write({'state': 'rejected'})
        return True

    def action_retry(self):
        """Retry a failed query."""
        self.write({
            'state': 'processing',
            'retry_count': self.retry_count + 1,
            'error_message': False,
        })
        return True


# =============================================================================
# EMAIL INTELLIGENCE
# =============================================================================

class CrmAiEmailIntelligence(models.Model):
    """Email Intelligence - AI analysis of customer emails.

    Extracts sentiment, action items, urgency, and relationship signals
    from email communications.
    """
    _name = 'crm.ai.email.intelligence'
    _description = 'Email Intelligence'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'email_date desc, id desc'

    name = fields.Char(
        string='Subject',
        required=True,
        tracking=True,
    )
    email_from = fields.Char(
        string='From',
        tracking=True,
    )
    email_to = fields.Char(
        string='To',
    )
    email_cc = fields.Char(string='CC')
    email_date = fields.Datetime(
        string='Email Date',
        required=True,
        tracking=True,
    )

    # Content
    body_text = fields.Text(string='Email Body (Text)')
    body_html = fields.Html(string='Email Body (HTML)')

    # AI Analysis Results
    sentiment = fields.Selection(
        [
            ('very_negative', 'Very Negative'),
            ('negative', 'Negative'),
            ('neutral', 'Neutral'),
            ('positive', 'Positive'),
            ('very_positive', 'Very Positive'),
        ],
        default='neutral',
        tracking=True,
    )
    sentiment_score = fields.Float(
        string='Sentiment Score',
        help='Numerical sentiment score from -1.0 to 1.0',
    )

    urgency = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        tracking=True,
    )

    # Extracted items
    action_items = fields.Text(
        string='Action Items',
        help='JSON array of extracted action items.',
    )
    key_topics = fields.Text(
        string='Key Topics',
        help='JSON array of key topics discussed.',
    )
    questions_asked = fields.Text(
        string='Questions Asked',
        help='JSON array of questions that need responses.',
    )

    # Signals generated
    signal_ids = fields.One2many(
        'crm.ai.relationship.signal',
        'email_id',
        string='Generated Signals',
    )
    signal_count = fields.Integer(
        compute='_compute_signal_count',
        string='Signal Count',
    )

    # Classification
    category = fields.Selection(
        [
            ('support', 'Support Request'),
            ('sales', 'Sales Inquiry'),
            ('complaint', 'Complaint'),
            ('feedback', 'Feedback'),
            ('renewal', 'Renewal Discussion'),
            ('upsell', 'Upsell Opportunity'),
            ('churn_risk', 'Churn Risk Indicator'),
            ('general', 'General Communication'),
        ],
        default='general',
        tracking=True,
    )

    # Processing status
    processing_status = fields.Selection(
        [
            ('new', 'New'),
            ('processing', 'Processing'),
            ('processed', 'Processed'),
            ('failed', 'Failed'),
        ],
        default='new',
        required=True,
        tracking=True,
    )

    # Linked records
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True,
    )
    opportunity_ref = fields.Reference(
        selection='_get_referenceable_models',
        string='Related Opportunity',
    )
    team_id = fields.Many2one(
        'crm.ai.agent.team',
        string='Team',
    )

    # AI metadata
    ai_model = fields.Char(string='AI Model Used')
    ai_processed_date = fields.Datetime(string='AI Processed Date')

    @api.model
    def _get_referenceable_models(self):
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    @api.depends('signal_ids')
    def _compute_signal_count(self):
        for record in self:
            record.signal_count = len(record.signal_ids)

    def action_process(self):
        """Process the email with AI analysis."""
        for email in self:
            email.write({'processing_status': 'processing'})
            try:
                # Placeholder for actual AI processing
                email._analyze_email()
                email.write({
                    'processing_status': 'processed',
                    'ai_processed_date': fields.Datetime.now(),
                })
            except Exception as e:
                email.write({
                    'processing_status': 'failed',
                    'error_message': str(e),
                })

    def _analyze_email(self):
        """Perform AI analysis on email content.

        This is a placeholder that should be extended by LLM provider modules.
        """
        self.ensure_one()
        # Placeholder implementation - override in LLM provider modules
        self.sentiment = 'neutral'
        self.urgency = 'medium'
        self.category = 'general'


# =============================================================================
# CUSTOMER HEALTH SCORING
# =============================================================================

class CrmAiCustomerHealth(models.Model):
    """Customer Health Score - Track customer health and engagement metrics.

    Aggregates multiple signals to provide a holistic view of customer health
    and churn risk.
    """
    _name = 'crm.ai.customer.health'
    _description = 'Customer Health Score'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'health_score asc, id desc'  # Show at-risk customers first

    name = fields.Char(
        compute='_compute_name',
        string='Name',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        index=True,
    )

    # Health Score Components (0-100 scale)
    health_score = fields.Integer(
        string='Health Score',
        compute='_compute_health_score',
        store=True,
        help='Overall health score (0-100). Higher is better.',
    )
    health_category = fields.Selection(
        [
            ('healthy', 'Healthy (80-100)'),
            ('stable', 'Stable (60-79)'),
            ('at_risk', 'At Risk (40-59)'),
            ('critical', 'Critical (0-39)'),
        ],
        compute='_compute_health_score',
        store=True,
        string='Health Category',
    )

    # Component Scores (weighted)
    engagement_score = fields.Integer(
        string='Engagement Score',
        default=50,
        tracking=True,
        help='Based on email opens, meeting attendance, portal logins.',
    )
    product_usage_score = fields.Integer(
        string='Product Usage Score',
        default=50,
        tracking=True,
        help='Based on feature adoption, usage frequency, active users.',
    )
    support_score = fields.Integer(
        string='Support Score',
        default=50,
        tracking=True,
        help='Based on ticket volume, resolution time, satisfaction.',
    )
    payment_score = fields.Integer(
        string='Payment Score',
        default=50,
        tracking=True,
        help='Based on payment timeliness, outstanding balance.',
    )
    sentiment_score = fields.Integer(
        string='Sentiment Score',
        default=50,
        tracking=True,
        help='Based on email/conversation sentiment trends.',
    )

    # Component Weights (configurable)
    engagement_weight = fields.Integer(default=25, string='Engagement Weight')
    product_usage_weight = fields.Integer(default=30, string='Product Usage Weight')
    support_weight = fields.Integer(default=20, string='Support Weight')
    payment_weight = fields.Integer(default=15, string='Payment Weight')
    sentiment_weight = fields.Integer(default=10, string='Sentiment Weight')

    # Trends
    health_trend = fields.Selection(
        [
            ('improving', 'Improving'),
            ('stable', 'Stable'),
            ('declining', 'Declining'),
            ('critical_decline', 'Critical Decline'),
        ],
        default='stable',
        tracking=True,
    )
    previous_health_score = fields.Integer(
        string='Previous Score',
        help='Health score from the last calculation.',
    )
    score_change = fields.Integer(
        compute='_compute_score_change',
        string='Score Change',
    )

    # Risk indicators
    churn_risk_level = fields.Selection(
        [
            ('none', 'No Risk'),
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('critical', 'Critical Risk'),
        ],
        compute='_compute_churn_risk',
        store=True,
        string='Churn Risk Level',
    )
    risk_factors = fields.Text(
        string='Risk Factors',
        help='JSON array of identified risk factors.',
    )
    recommended_actions = fields.Text(
        string='Recommended Actions',
        help='AI-recommended actions to improve health.',
    )

    # Metrics
    days_since_last_contact = fields.Integer(
        string='Days Since Last Contact',
        compute='_compute_contact_metrics',
        store=True,
    )
    open_tickets = fields.Integer(
        string='Open Support Tickets',
        compute='_compute_support_metrics',
        store=True,
    )
    overdue_amount = fields.Float(
        string='Overdue Amount',
        compute='_compute_payment_metrics',
        store=True,
    )

    # History tracking
    history_ids = fields.One2many(
        'crm.ai.customer.health.history',
        'health_id',
        string='Score History',
    )

    # Linked signals
    signal_ids = fields.One2many(
        'crm.ai.relationship.signal',
        'health_id',
        string='Related Signals',
    )

    @api.depends('partner_id')
    def _compute_name(self):
        for record in self:
            record.name = f"Health: {record.partner_id.name}" if record.partner_id else "New Health Score"

    @api.depends(
        'engagement_score', 'product_usage_score', 'support_score',
        'payment_score', 'sentiment_score',
        'engagement_weight', 'product_usage_weight', 'support_weight',
        'payment_weight', 'sentiment_weight'
    )
    def _compute_health_score(self):
        for record in self:
            total_weight = (
                record.engagement_weight + record.product_usage_weight +
                record.support_weight + record.payment_weight + record.sentiment_weight
            )
            if total_weight == 0:
                total_weight = 100

            weighted_score = (
                record.engagement_score * record.engagement_weight +
                record.product_usage_score * record.product_usage_weight +
                record.support_score * record.support_weight +
                record.payment_score * record.payment_weight +
                record.sentiment_score * record.sentiment_weight
            )

            record.health_score = int(weighted_score / total_weight)

            if record.health_score >= 80:
                record.health_category = 'healthy'
            elif record.health_score >= 60:
                record.health_category = 'stable'
            elif record.health_score >= 40:
                record.health_category = 'at_risk'
            else:
                record.health_category = 'critical'

    @api.depends('health_score', 'previous_health_score')
    def _compute_score_change(self):
        for record in self:
            if record.previous_health_score:
                record.score_change = record.health_score - record.previous_health_score
            else:
                record.score_change = 0

    @api.depends('health_score', 'health_category')
    def _compute_churn_risk(self):
        for record in self:
            if record.health_score >= 80:
                record.churn_risk_level = 'none'
            elif record.health_score >= 60:
                record.churn_risk_level = 'low'
            elif record.health_score >= 40:
                record.churn_risk_level = 'medium'
            elif record.health_score >= 20:
                record.churn_risk_level = 'high'
            else:
                record.churn_risk_level = 'critical'

    @api.depends('partner_id')
    def _compute_contact_metrics(self):
        for record in self:
            if record.partner_id:
                # Find last activity/contact
                last_activity = self.env['mail.activity'].search([
                    ('res_partner_id', '=', record.partner_id.id),
                ], order='write_date desc', limit=1)
                if last_activity:
                    delta = fields.Datetime.now() - last_activity.write_date
                    record.days_since_last_contact = delta.days
                else:
                    record.days_since_last_contact = 999
            else:
                record.days_since_last_contact = 0

    @api.depends('partner_id')
    def _compute_support_metrics(self):
        for record in self:
            if record.partner_id and self.env.registry.get('helpdesk.ticket') is not None:
                open_tickets = self.env['helpdesk.ticket'].search_count([
                    ('partner_id', '=', record.partner_id.id),
                    ('stage_id.is_close', '=', False),
                ])
                record.open_tickets = open_tickets
            else:
                record.open_tickets = 0

    @api.depends('partner_id')
    def _compute_payment_metrics(self):
        for record in self:
            if record.partner_id:
                record.overdue_amount = record.partner_id.credit or 0.0
            else:
                record.overdue_amount = 0.0

    def action_recalculate(self):
        """Recalculate health score from current data."""
        for record in self:
            # Store previous score for trend analysis
            record.previous_health_score = record.health_score

            # Update trend based on score change
            if record.previous_health_score:
                change = record.health_score - record.previous_health_score
                if change >= 5:
                    record.health_trend = 'improving'
                elif change <= -15:
                    record.health_trend = 'critical_decline'
                elif change <= -5:
                    record.health_trend = 'declining'
                else:
                    record.health_trend = 'stable'

            # Create history record
            self.env['crm.ai.customer.health.history'].create({
                'health_id': record.id,
                'health_score': record.health_score,
                'engagement_score': record.engagement_score,
                'product_usage_score': record.product_usage_score,
                'support_score': record.support_score,
                'payment_score': record.payment_score,
                'sentiment_score': record.sentiment_score,
            })

        return True


class CrmAiCustomerHealthHistory(models.Model):
    """Historical record of customer health scores."""
    _name = 'crm.ai.customer.health.history'
    _description = 'Customer Health History'
    _order = 'create_date desc, id desc'

    health_id = fields.Many2one(
        'crm.ai.customer.health',
        required=True,
        ondelete='cascade',
        index=True,
    )
    health_score = fields.Integer(string='Health Score')
    engagement_score = fields.Integer(string='Engagement Score')
    product_usage_score = fields.Integer(string='Product Usage Score')
    support_score = fields.Integer(string='Support Score')
    payment_score = fields.Integer(string='Payment Score')
    sentiment_score = fields.Integer(string='Sentiment Score')


# =============================================================================
# ENHANCED OBSERVABILITY
# =============================================================================

class CrmAiToolRun(models.Model):
    """Tool Run - Detailed execution record for observability.

    Provides step-by-step visibility into AI tool executions with
    timing, tokens, costs, and error tracking.
    """
    _name = 'crm.ai.tool.run'
    _description = 'AI Tool Run'
    _inherit = ['mail.thread']
    _order = 'start_time desc, id desc'

    name = fields.Char(
        string='Run Name',
        required=True,
        tracking=True,
    )
    tool_name = fields.Char(
        string='Tool Name',
        required=True,
        index=True,
    )
    tool_type = fields.Selection(
        [
            ('mcp', 'MCP Tool'),
            ('agent', 'Agent Pipeline'),
            ('nl_query', 'Natural Language Query'),
            ('email_analysis', 'Email Analysis'),
            ('health_calc', 'Health Calculation'),
        ],
        string='Tool Type',
        required=True,
        index=True,
    )

    # Timing
    start_time = fields.Datetime(
        string='Start Time',
        required=True,
        index=True,
    )
    end_time = fields.Datetime(
        string='End Time',
    )
    duration_ms = fields.Integer(
        string='Duration (ms)',
        compute='_compute_duration',
        store=True,
    )
    ttfb_ms = fields.Integer(
        string='Time to First Byte (ms)',
        help='Time until first response token in streaming mode.',
    )

    # Status
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
            ('requires_approval', 'Requires Approval'),
        ],
        default='pending',
        required=True,
        tracking=True,
        index=True,
    )

    # Token and Cost Tracking
    input_tokens = fields.Integer(string='Input Tokens')
    output_tokens = fields.Integer(string='Output Tokens')
    total_tokens = fields.Integer(
        string='Total Tokens',
        compute='_compute_total_tokens',
        store=True,
    )
    estimated_cost = fields.Float(
        string='Estimated Cost (USD)',
        digits=(10, 6),
    )
    model_name = fields.Char(string='Model Used')

    # Input/Output
    input_data = fields.Text(
        string='Input Data (JSON)',
        help='JSON representation of tool input.',
    )
    output_data = fields.Text(
        string='Output Data (JSON)',
        help='JSON representation of tool output.',
    )
    error_data = fields.Text(
        string='Error Data (JSON)',
        help='Error details if the run failed.',
    )

    # Reasoning Chain
    reasoning_steps = fields.One2many(
        'crm.ai.tool.run.step',
        'run_id',
        string='Reasoning Steps',
    )
    step_count = fields.Integer(
        compute='_compute_step_count',
        string='Step Count',
    )

    # Linked records
    user_id = fields.Many2one(
        'res.users',
        string='Triggered By',
        default=lambda self: self.env.user.id,
    )
    team_id = fields.Many2one(
        'crm.ai.agent.team',
        string='Team',
        index=True,
    )
    nl_query_id = fields.Many2one(
        'crm.ai.nl.query',
        string='NL Query',
    )
    email_id = fields.Many2one(
        'crm.ai.email.intelligence',
        string='Email Analysis',
    )
    health_id = fields.Many2one(
        'crm.ai.customer.health',
        string='Health Check',
    )

    # Environment context
    environment = fields.Selection(
        [
            ('development', 'Development'),
            ('staging', 'Staging'),
            ('production', 'Production'),
        ],
        default='production',
        string='Environment',
    )
    session_id = fields.Char(
        string='Session ID',
        index=True,
        help='Groups multiple runs in a single conversation session.',
    )

    # Human-in-the-loop
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
    )
    approved_date = fields.Datetime(string='Approved Date')
    rejected_by = fields.Many2one(
        'res.users',
        string='Rejected By',
    )
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.depends('input_tokens', 'output_tokens')
    def _compute_total_tokens(self):
        for record in self:
            record.total_tokens = (record.input_tokens or 0) + (record.output_tokens or 0)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration_ms = int(delta.total_seconds() * 1000)
            else:
                record.duration_ms = 0

    @api.depends('reasoning_steps')
    def _compute_step_count(self):
        for record in self:
            record.step_count = len(record.reasoning_steps)

    def action_approve(self):
        """Approve this tool run for execution."""
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        return True

    def action_reject(self, reason=''):
        """Reject this tool run."""
        self.write({
            'state': 'rejected',
            'rejected_by': self.env.user.id,
            'rejection_reason': reason,
        })
        return True


class CrmAiToolRunStep(models.Model):
    """Tool Run Step - Individual step in a tool's reasoning chain.

    Provides detailed visibility into each step of AI execution,
    including LLM calls, tool invocations, and data transformations.
    """
    _name = 'crm.ai.tool.run.step'
    _description = 'Tool Run Step'
    _order = 'sequence, id'

    run_id = fields.Many2one(
        'crm.ai.tool.run',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)

    # Step identification
    name = fields.Char(
        string='Step Name',
        required=True,
    )
    step_type = fields.Selection(
        [
            ('llm_call', 'LLM Call'),
            ('tool_call', 'Tool Call'),
            ('retrieval', 'Data Retrieval'),
            ('transformation', 'Data Transformation'),
            ('decision', 'Decision Point'),
            ('output', 'Output Generation'),
        ],
        required=True,
        string='Step Type',
    )

    # Timing
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration_ms = fields.Integer(
        string='Duration (ms)',
        compute='_compute_duration',
        store=True,
    )

    # Token tracking (for LLM calls)
    input_tokens = fields.Integer(string='Input Tokens')
    output_tokens = fields.Integer(string='Output Tokens')

    # Status
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
        ],
        default='pending',
        required=True,
    )

    # Content
    input_data = fields.Text(string='Input Data (JSON)')
    output_data = fields.Text(string='Output Data (JSON)')
    error_message = fields.Text(string='Error Message')

    # Metadata
    metadata = fields.Text(
        string='Metadata (JSON)',
        help='Additional metadata like model name, temperature, etc.',
    )

    # Parent-child relationships (for nested calls)
    parent_step_id = fields.Many2one(
        'crm.ai.tool.run.step',
        string='Parent Step',
        ondelete='cascade',
    )
    child_step_ids = fields.One2many(
        'crm.ai.tool.run.step',
        'parent_step_id',
        string='Child Steps',
    )

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration_ms = int(delta.total_seconds() * 1000)
            else:
                record.duration_ms = 0


# =============================================================================
# UPDATE RELATIONSHIP SIGNAL FOR NEW RELATIONSHIPS
# =============================================================================

# Add relationships to existing CrmAiRelationshipSignal model
# This would be done via inheritance in a separate file, but included here for reference
class CrmAiRelationshipSignalExtended(models.Model):
    """Extend Relationship Signal with new relationships."""
    _inherit = 'crm.ai.relationship.signal'

    email_id = fields.Many2one(
        'crm.ai.email.intelligence',
        string='Source Email',
    )
    health_id = fields.Many2one(
        'crm.ai.customer.health',
        string='Source Health Check',
    )
    nl_query_id = fields.Many2one(
        'crm.ai.nl.query',
        string='Source NL Query',
    )

import random

from odoo import api, fields, models


class CrmAiAgentTeam(models.Model):
    """AI Agent Team configuration with LLM provider settings.

    Teams can be configured to use different LLM providers and models.
    Settings cascade to agents unless overridden at agent level.
    """
    _name = 'crm.ai.agent.team'
    _description = 'AI Agent Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    member_ids = fields.One2many('crm.ai.agent', 'team_id', string='Agents')
    summary_ids = fields.One2many('crm.ai.conversation.summary', 'team_id', string='Conversation Summaries')
    run_ids = fields.One2many('crm.ai.agent.run', 'team_id', string='Agent Runs')
    run_count = fields.Integer(compute='_compute_run_metrics')
    last_run_date = fields.Datetime(compute='_compute_run_metrics')
    last_run_status = fields.Selection(
        [('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')],
        compute='_compute_run_metrics',
    )

    # LLM Provider Configuration (Team-level defaults)
    llm_provider = fields.Selection(
        [
            ('openai', 'OpenAI'),
            ('anthropic', 'Anthropic'),
            ('google', 'Google AI'),
            ('azure', 'Azure OpenAI'),
            ('local', 'Local Model'),
            ('none', 'None (Rule-based)'),
        ],
        default='none',
        string='LLM Provider',
        tracking=True,
        help='AI provider for this team. Agents can override this setting.',
    )
    llm_model = fields.Char(
        string='Model Name',
        tracking=True,
        help='Specific model to use (e.g., gpt-4, claude-3-opus, gemini-pro)',
    )
    llm_api_endpoint = fields.Char(
        string='API Endpoint',
        tracking=True,
        help='Custom API endpoint URL. Leave empty for provider defaults.',
    )
    llm_temperature = fields.Float(
        string='Temperature',
        default=0.7,
        tracking=True,
        help='Sampling temperature (0.0-2.0). Lower = more deterministic.',
    )
    llm_max_tokens = fields.Integer(
        string='Max Tokens',
        default=4096,
        tracking=True,
        help='Maximum tokens in response.',
    )
    llm_system_prompt = fields.Text(
        string='System Prompt',
        tracking=True,
        help='Default system prompt for all agents in this team.',
    )

    @api.depends('run_ids.status', 'run_ids.end_datetime')
    def _compute_run_metrics(self):
        for team in self:
            team.run_count = len(team.run_ids)
            last_run = team.run_ids.sorted('end_datetime', reverse=True)[:1]
            if last_run:
                team.last_run_date = last_run.end_datetime
                team.last_run_status = last_run.status
            else:
                team.last_run_date = False
                team.last_run_status = False

    def action_run_agent_team(self):
        for team in self:
            team._run_agent_team_pipeline()
        return True

    def _run_agent_team_pipeline(self):
        self.ensure_one()
        pending_summaries = self.summary_ids.filtered(lambda summary: not summary.processed)
        run = self.env['crm.ai.agent.run'].create(
            {
                'name': f'{self.name} / {fields.Datetime.now()}',
                'team_id': self.id,
                'start_datetime': fields.Datetime.now(),
            }
        )
        success_steps = 0
        failed_steps = 0
        for summary in pending_summaries:
            for agent in self.member_ids:
                try:
                    action = summary._apply_agent_logic(agent)
                    self.env['crm.ai.agent.run.log'].create(
                        {
                            'run_id': run.id,
                            'summary_id': summary.id,
                            'agent_id': agent.id,
                            'log_level': 'info',
                            'message': action,
                        }
                    )
                    success_steps += 1
                except Exception as err:  # noqa: BLE001
                    self.env['crm.ai.agent.run.log'].create(
                        {
                            'run_id': run.id,
                            'summary_id': summary.id,
                            'agent_id': agent.id,
                            'log_level': 'error',
                            'message': str(err),
                        }
                    )
                    failed_steps += 1
            summary.processed = True

        status = 'success'
        if failed_steps and success_steps:
            status = 'partial'
        elif failed_steps and not success_steps:
            status = 'failed'
        run.write(
            {
                'end_datetime': fields.Datetime.now(),
                'status': status,
                'processed_summary_count': len(pending_summaries),
                'success_step_count': success_steps,
                'failed_step_count': failed_steps,
            }
        )
        return run

    @api.model
    def create_dummy_dataset(self, team_name='AI Demo Team', agent_count=5, transcript_count=20, auto_run=True):
        """Programmatically create a realistic demo dataset for this module.

        The method creates a team, agents, themes, customers, opportunities,
        meeting transcripts and summaries. It can also execute the team pipeline.

        This method now works without CRM dependency - it only creates
        crm.lead records if the CRM module is installed.
        """
        rng = random.Random(42)
        team = self.create({'name': team_name})

        roles = [
            'relationship_manager',
            'sales_specialist',
            'renewal_specialist',
            'support_specialist',
            'risk_analyst',
        ]
        for index in range(agent_count):
            role = roles[index % len(roles)]
            self.env['crm.ai.agent'].create(
                {
                    'name': f'{team_name} Agent {index + 1}',
                    'team_id': team.id,
                    'role': role,
                    'instruction': f'Handle {role.replace("_", " ")} tasks with clear next actions.',
                }
            )

        theme_values = [
            ('cross_sell', 'Cross-sell'),
            ('upsell', 'Upsell'),
            ('renewal', 'Renewal'),
            ('churn_risk', 'Churn Risk'),
            ('support_case', 'Support Case'),
            ('product_feedback', 'Product Feedback'),
            ('general', 'General'),
        ]
        for code, name in theme_values:
            if not self.env['crm.ai.theme'].search_count([('code', '=', code)]):
                self.env['crm.ai.theme'].create({'name': name, 'code': code})

        transcript_templates = [
            'Customer is happy with product value and asked about upgrade options for the next quarter.',
            'Customer reported a ticket and a bug incident, but is open to contract renewal conversation.',
            'Customer is at risk to churn and may cancel due to recent downtime and unresolved issue.',
            'Customer requested feature feedback review and discussed cross-sell for adjacent product lines.',
            'Customer asked for enterprise plan pricing, upsell options, and renewal terms before expiration.',
        ]
        providers = ['zoom', 'microsoft_teams', 'google_meet', 'other']

        # Check if CRM module is installed for opportunity creation
        crm_installed = self.env.registry.get('crm.lead') is not None

        for index in range(transcript_count):
            partner = self.env['res.partner'].create({'name': f'{team_name} Customer {index + 1}'})

            # Only create crm.lead if CRM is installed
            opportunity_ref = False
            if crm_installed:
                opportunity = self.env['crm.lead'].create(
                    {
                        'name': f'{team_name} Opportunity {index + 1}',
                        'type': 'opportunity',
                        'partner_id': partner.id,
                        'expected_revenue': 1000 + rng.randint(0, 20000),
                    }
                )
                opportunity_ref = f'crm.lead,{opportunity.id}'

            sentence = transcript_templates[index % len(transcript_templates)]
            transcript = self.env['crm.ai.meeting.transcript'].create(
                {
                    'name': f'{team_name} Meeting {index + 1}',
                    'provider': providers[index % len(providers)],
                    'external_ref': f'{team.id}-{index + 1}',
                    'partner_id': partner.id,
                    'team_id': team.id,
                    'opportunity_ref': opportunity_ref,
                    'raw_transcript': f'{sentence}\nAction item #{index + 1}',
                }
            )
            transcript.action_process_transcript()

        if auto_run:
            team.action_run_agent_team()

        return {
            'team_id': team.id,
            'agent_count': len(team.member_ids),
            'transcript_count': transcript_count,
            'summary_count': self.env['crm.ai.conversation.summary'].search_count([('team_id', '=', team.id)]),
            'run_count': self.env['crm.ai.agent.run'].search_count([('team_id', '=', team.id)]),
        }


class CrmAiAgent(models.Model):
    """AI Agent profile with role, instructions, and LLM configuration.

    Agents inherit LLM settings from their team but can override them.
    Each agent has a role and can be configured with custom prompts.
    """
    _name = 'crm.ai.agent'
    _description = 'AI Agent Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    team_id = fields.Many2one('crm.ai.agent.team', required=True, ondelete='cascade', tracking=True)
    role = fields.Selection(
        [
            ('relationship_manager', 'Relationship Manager'),
            ('sales_specialist', 'Sales Specialist'),
            ('renewal_specialist', 'Renewal Specialist'),
            ('support_specialist', 'Support Specialist'),
            ('risk_analyst', 'Risk Analyst'),
        ],
        required=True,
        default='relationship_manager',
        tracking=True,
    )
    instruction = fields.Text(
        tracking=True,
        help='Base instruction/prompt for this agent. Can use {customer}, {summary}, {themes} placeholders.',
    )

    # Agent-level LLM overrides (optional)
    llm_provider = fields.Selection(
        [
            ('openai', 'OpenAI'),
            ('anthropic', 'Anthropic'),
            ('google', 'Google AI'),
            ('azure', 'Azure OpenAI'),
            ('local', 'Local Model'),
            ('inherit', 'Inherit from Team'),
        ],
        default='inherit',
        string='LLM Provider',
        tracking=True,
        help='Override team LLM provider, or inherit from team.',
    )
    llm_model = fields.Char(
        string='Model Name',
        tracking=True,
        help='Override model name for this agent.',
    )
    llm_temperature = fields.Float(
        string='Temperature',
        tracking=True,
        help='Override sampling temperature for this agent.',
    )
    llm_max_tokens = fields.Integer(
        string='Max Tokens',
        tracking=True,
        help='Override max tokens for this agent.',
    )

    # Prompt configuration
    system_prompt = fields.Text(
        string='System Prompt',
        tracking=True,
        help='Agent-specific system prompt. Use placeholders: {role}, {customer}, {summary}, {themes}.',
    )
    response_format = fields.Selection(
        [
            ('text', 'Plain Text'),
            ('json', 'JSON'),
            ('markdown', 'Markdown'),
        ],
        default='text',
        string='Response Format',
        tracking=True,
    )

    # Tool definitions for this agent (JSON schema)
    tool_definitions = fields.Text(
        string='Tool Definitions (JSON)',
        tracking=True,
        help='JSON array of tool/function definitions this agent can use. Follow OpenAI function calling schema.',
    )

    @api.onchange('team_id')
    def _onchange_team_id(self):
        """Populate default prompts from team if available."""
        if self.team_id and not self.system_prompt:
            self.system_prompt = self.team_id.llm_system_prompt


class CrmAiTheme(models.Model):
    """Conversation theme classification for AI analysis."""
    _name = 'crm.ai.theme'
    _description = 'AI Conversation Theme'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    code = fields.Selection(
        [
            ('cross_sell', 'Cross-sell'),
            ('upsell', 'Upsell'),
            ('renewal', 'Renewal'),
            ('churn_risk', 'Churn Risk'),
            ('support_case', 'Support Case'),
            ('product_feedback', 'Product Feedback'),
            ('general', 'General'),
        ],
        required=True,
        default='general',
        tracking=True,
    )
    description = fields.Text(tracking=True)
    priority_weight = fields.Float(
        default=1.0,
        string='Priority Weight',
        tracking=True,
        help='Weight factor for signal priority calculation. Higher = more urgent.',
    )


class CrmAiConversationSummary(models.Model):
    """AI-processed conversation summary with embeddings and semantic data.

    Stores the processed output from meeting transcripts or manual entries,
    including sentiment, themes, and vector embeddings for semantic search.
    """
    _name = 'crm.ai.conversation.summary'
    _description = 'AI Conversation Summary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'conversation_datetime desc, id desc'

    name = fields.Char(required=True, tracking=True)
    conversation_datetime = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    team_id = fields.Many2one('crm.ai.agent.team', tracking=True)
    agent_id = fields.Many2one('crm.ai.agent', string='Primary Agent', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    sentiment = fields.Selection(
        [
            ('very_negative', 'Very Negative'),
            ('negative', 'Negative'),
            ('neutral', 'Neutral'),
            ('positive', 'Positive'),
            ('very_positive', 'Very Positive'),
        ],
        default='neutral',
        required=True,
        tracking=True,
    )
    summary = fields.Text(required=True)
    key_points = fields.Text(help='Structured key takeaways extracted by AI agents.')
    theme_ids = fields.Many2many('crm.ai.theme', string='Themes')

    # CRM decoupling: Use Reference field instead of Many2one to crm.lead
    # This allows the addon to work without CRM module installed
    opportunity_ref = fields.Reference(
        selection='_get_opportunity_models',
        string='Opportunity',
        tracking=True,
        help='Linked sales opportunity. Works with CRM or other sales modules.',
    )
    # Keep opportunity_id for backward compatibility (computed from opportunity_ref if CRM installed)
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Sales Opportunity (Legacy)',
        compute='_compute_opportunity_id',
        inverse='_inverse_opportunity_id',
        store=True,
        help='Legacy field for backward compatibility. Use opportunity_ref for new code.',
    )
    case_ref = fields.Reference(
        selection='_referenceable_models',
        string='Case',
        help='Optional case/ticket linked to this summary.',
    )
    signal_ids = fields.One2many('crm.ai.relationship.signal', 'summary_id', string='Relationship Signals')
    transcript_id = fields.Many2one('crm.ai.meeting.transcript', string='Source Transcript', index=True)
    processed = fields.Boolean(default=False, tracking=True)

    # Vector embeddings for semantic search
    embedding_vector = fields.Binary(
        attachment=True,
        string='Embedding Vector',
        help='Binary storage for the embedding vector of this summary.',
    )
    embedding_model = fields.Char(
        string='Embedding Model',
        help='Model used to generate embeddings (e.g., text-embedding-3-small).',
    )
    embedding_dimension = fields.Integer(
        string='Embedding Dimension',
        help='Dimension of the embedding vector (e.g., 1536 for OpenAI embeddings).',
    )
    embedding_timestamp = fields.Datetime(
        string='Embedding Generated',
        help='When the embedding was last generated.',
    )

    # AI processing metadata
    ai_processed = fields.Boolean(
        default=False,
        string='AI Processed',
        help='Whether AI has enhanced this summary (e.g., LLM analysis).',
    )
    ai_model_version = fields.Char(
        string='AI Model Version',
        help='Version of AI model used for processing.',
    )

    @api.model
    def _get_opportunity_models(self):
        """Get available opportunity models based on installed modules."""
        models = []
        # Check if CRM is installed
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        # Add other potential opportunity/sales models here
        return models

    @api.model
    def _referenceable_models(self):
        model_names = ['helpdesk.ticket', 'project.task', 'crm.lead']
        models = self.env['ir.model'].sudo().search([('model', 'in', model_names)])
        return [(model.model, model.name) for model in models if self.env.registry.get(model.model) is not None]

    @api.depends('opportunity_ref')
    def _compute_opportunity_id(self):
        """Compute legacy opportunity_id from opportunity_ref."""
        for record in self:
            if record.opportunity_ref and record.opportunity_ref._name == 'crm.lead':
                record.opportunity_id = record.opportunity_ref.id
            else:
                record.opportunity_id = False

    def _inverse_opportunity_id(self):
        """Set opportunity_ref from legacy opportunity_id."""
        for record in self:
            if record.opportunity_id:
                record.opportunity_ref = f'crm.lead,{record.opportunity_id.id}'
            else:
                record.opportunity_ref = False

    def _apply_agent_logic(self, agent):
        self.ensure_one()

        # Check if configurable rules exist
        rules = self.env['crm.ai.signal.rule'].search([('active', '=', True)], order='sequence')
        if rules:
            # Use configurable rules
            return self._apply_configurable_rules(agent, rules)

        # Fall back to hardcoded logic for backward compatibility
        signal_vals = self._build_signal_vals(agent)
        if signal_vals:
            self.env['crm.ai.relationship.signal'].create(signal_vals)
            return f"Created signal '{signal_vals['signal_type']}' for summary '{self.name}'."
        return f"No signal created for summary '{self.name}' by agent '{agent.name}'."

    def _apply_configurable_rules(self, agent, rules):
        """Apply configurable signal rules to determine actions."""
        for rule in rules:
            if rule.matches_conditions(self, agent):
                signal_vals = rule.create_signal_values(self, agent)
                if signal_vals:
                    self.env['crm.ai.relationship.signal'].create(signal_vals)
                    return f"Rule '{rule.name}' triggered signal '{signal_vals['signal_type']}' for summary '{self.name}'."
        return f"No matching rules for summary '{self.name}' by agent '{agent.name}'."

    def _build_signal_vals(self, agent):
        """Legacy hardcoded signal generation logic.

        Kept for backward compatibility when no configurable rules exist.
        """
        self.ensure_one()
        signal_type = False
        priority = 'medium'
        confidence = 0.6
        recommendation = False
        theme_codes = set(self.theme_ids.mapped('code'))

        if self.sentiment in ('very_negative', 'negative') or 'churn_risk' in theme_codes:
            signal_type = 'churn_risk'
            priority = 'high' if self.sentiment == 'very_negative' else 'medium'
            confidence = 0.9 if self.sentiment == 'very_negative' else 0.75
            recommendation = 'Escalate to retention workflow and schedule executive check-in.'
        elif 'renewal' in theme_codes or agent.role == 'renewal_specialist':
            signal_type = 'renewal'
            priority = 'high' if self.sentiment == 'neutral' else 'medium'
            confidence = 0.7
            recommendation = 'Prepare renewal plan, confirm timing, and align terms with customer goals.'
        elif 'upsell' in theme_codes or agent.role == 'sales_specialist':
            signal_type = 'upsell'
            priority = 'medium'
            confidence = 0.65
            recommendation = 'Propose expanded package tied to customer outcomes discussed.'
        elif 'cross_sell' in theme_codes:
            signal_type = 'cross_sell'
            priority = 'low'
            confidence = 0.6
            recommendation = 'Recommend adjacent product aligned with identified use case.'

        if not signal_type:
            return False

        # Use opportunity_ref if available, fall back to opportunity_id
        lead_id = False
        if self.opportunity_ref and self.opportunity_ref._name == 'crm.lead':
            lead_id = self.opportunity_ref.id
        elif self.opportunity_id:
            lead_id = self.opportunity_id.id

        return {
            'summary_id': self.id,
            'signal_type': signal_type,
            'priority': priority,
            'confidence': confidence,
            'recommendation': recommendation,
            'lead_ref': f'crm.lead,{lead_id}' if lead_id else False,
            'owner_id': self.env.user.id,
        }

    def action_generate_embedding(self):
        """Trigger embedding generation for selected summaries.

        This method is a placeholder that can be extended by LLM provider modules.
        """
        # Placeholder - actual implementation would call an embedding API
        for summary in self:
            summary.embedding_timestamp = fields.Datetime.now()
        return True

    def action_reprocess_with_ai(self):
        """Reprocess summary with AI to enhance analysis."""
        for summary in self:
            summary.ai_processed = True
            summary.ai_model_version = 'manual'
        return True


class CrmAiSignalRule(models.Model):
    """Configurable signal generation rules.

    Rules are evaluated in sequence order. First matching rule determines
    the signal type, priority, and recommendation.
    """
    _name = 'crm.ai.signal.rule'
    _description = 'AI Signal Generation Rule'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(default=10, tracking=True)
    description = fields.Text(tracking=True)

    # Conditions
    condition_sentiment = fields.Selection(
        [
            ('any', 'Any'),
            ('very_negative', 'Very Negative'),
            ('negative', 'Negative'),
            ('neutral', 'Neutral'),
            ('positive', 'Positive'),
            ('very_positive', 'Very Positive'),
            ('negative_or_very_negative', 'Negative or Very Negative'),
            ('positive_or_very_positive', 'Positive or Very Positive'),
        ],
        default='any',
        string='Sentiment Condition',
        tracking=True,
    )
    condition_theme_ids = fields.Many2many(
        'crm.ai.theme',
        string='Required Themes',
        help='Summary must have at least one of these themes (OR logic).',
    )
    condition_agent_role = fields.Selection(
        [
            ('any', 'Any Role'),
            ('relationship_manager', 'Relationship Manager'),
            ('sales_specialist', 'Sales Specialist'),
            ('renewal_specialist', 'Renewal Specialist'),
            ('support_specialist', 'Support Specialist'),
            ('risk_analyst', 'Risk Analyst'),
        ],
        default='any',
        string='Agent Role Condition',
        tracking=True,
    )
    condition_expression = fields.Text(
        string='Custom Python Expression',
        help='Optional Python expression for advanced conditions. '
             'Variables: summary, agent. Example: summary.partner_id.category_id.filtered(lambda c: c.name == "VIP")',
    )

    # Actions
    action_signal_type = fields.Selection(
        [
            ('cross_sell', 'Cross-sell Opportunity'),
            ('upsell', 'Upsell Opportunity'),
            ('renewal', 'Renewal Action'),
            ('churn_risk', 'Churn Risk'),
        ],
        required=True,
        string='Signal Type',
        tracking=True,
    )
    action_priority = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium',
        required=True,
        tracking=True,
    )
    action_confidence = fields.Float(
        default=0.7,
        string='Confidence Score',
        tracking=True,
    )
    action_recommendation = fields.Text(
        required=True,
        string='Recommendation Template',
        help='Template for recommendation. Use {customer}, {themes}, {sentiment} placeholders.',
    )

    def matches_conditions(self, summary, agent):
        """Check if this rule matches the given summary and agent."""
        # Check sentiment condition
        if self.condition_sentiment != 'any':
            if self.condition_sentiment == 'negative_or_very_negative':
                if summary.sentiment not in ('negative', 'very_negative'):
                    return False
            elif self.condition_sentiment == 'positive_or_very_positive':
                if summary.sentiment not in ('positive', 'very_positive'):
                    return False
            elif summary.sentiment != self.condition_sentiment:
                return False

        # Check theme condition (OR logic - must have at least one)
        if self.condition_theme_ids:
            summary_theme_ids = set(summary.theme_ids.ids)
            rule_theme_ids = set(self.condition_theme_ids.ids)
            if not (summary_theme_ids & rule_theme_ids):
                return False

        # Check agent role condition
        if self.condition_agent_role != 'any' and agent.role != self.condition_agent_role:
            return False

        # Check custom expression
        if self.condition_expression:
            try:
                # Safe eval with limited globals
                result = eval(
                    self.condition_expression,
                    {'summary': summary, 'agent': agent, 'bool': bool, 'len': len},
                )
                if not result:
                    return False
            except Exception:
                return False

        return True

    def create_signal_values(self, summary, agent):
        """Create signal values dict for the matched rule."""
        # Format recommendation with placeholders
        recommendation = self.action_recommendation or ''
        themes_str = ', '.join(summary.theme_ids.mapped('name')) if summary.theme_ids else 'none'
        try:
            recommendation = recommendation.format(
                customer=summary.partner_id.name or 'Customer',
                themes=themes_str,
                sentiment=dict(summary._fields['sentiment'].get_description(summary.env)['selection']).get(
                    summary.sentiment, summary.sentiment
                ),
            )
        except KeyError:
            pass

        # Get lead reference
        lead_ref = False
        if summary.opportunity_ref:
            lead_ref = f'{summary.opportunity_ref._name},{summary.opportunity_ref.id}'

        return {
            'summary_id': summary.id,
            'signal_type': self.action_signal_type,
            'priority': self.action_priority,
            'confidence': self.action_confidence,
            'recommendation': recommendation,
            'lead_ref': lead_ref,
            'owner_id': self.env.user.id,
        }


class CrmAiAgentRun(models.Model):
    """Pipeline execution record with observability metrics."""
    _name = 'crm.ai.agent.run'
    _description = 'AI Agent Team Run'
    _inherit = ['mail.thread']
    _order = 'start_datetime desc, id desc'

    name = fields.Char(required=True, tracking=True)
    team_id = fields.Many2one('crm.ai.agent.team', required=True, ondelete='cascade', index=True, tracking=True)
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(tracking=True)
    status = fields.Selection(
        [('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')],
        default='success',
        required=True,
        index=True,
        tracking=True,
    )
    processed_summary_count = fields.Integer(default=0)
    success_step_count = fields.Integer(default=0)
    failed_step_count = fields.Integer(default=0)
    duration_seconds = fields.Float(compute='_compute_duration_seconds', store=True)
    log_ids = fields.One2many('crm.ai.agent.run.log', 'run_id', string='Run Logs')

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration_seconds(self):
        for run in self:
            if run.start_datetime and run.end_datetime:
                delta = fields.Datetime.to_datetime(run.end_datetime) - fields.Datetime.to_datetime(run.start_datetime)
                run.duration_seconds = delta.total_seconds()
            else:
                run.duration_seconds = 0.0


class CrmAiAgentRunLog(models.Model):
    """Detailed step execution log for observability."""
    _name = 'crm.ai.agent.run.log'
    _description = 'AI Agent Team Run Log'
    _order = 'create_date desc, id desc'

    run_id = fields.Many2one('crm.ai.agent.run', required=True, ondelete='cascade', index=True)
    team_id = fields.Many2one('crm.ai.agent.team', related='run_id.team_id', store=True)
    summary_id = fields.Many2one('crm.ai.conversation.summary', index=True)
    agent_id = fields.Many2one('crm.ai.agent', index=True)
    log_level = fields.Selection(
        [('debug', 'Debug'), ('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')],
        default='info',
        required=True,
        index=True,
    )
    message = fields.Text(required=True)
    extra_data = fields.Text(
        string='Extra Data (JSON)',
        help='Additional structured data in JSON format.',
    )


class CrmAiMeetingTranscript(models.Model):
    """Imported meeting transcript with automatic processing.

    Supports transcripts from Zoom, Teams, Meet, and other providers.
    Automatically processes to create conversation summaries.
    """
    _name = 'crm.ai.meeting.transcript'
    _description = 'AI Meeting Transcript'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_datetime desc, id desc'

    name = fields.Char(required=True, tracking=True)
    provider = fields.Selection(
        [
            ('zoom', 'Zoom'),
            ('microsoft_teams', 'Microsoft Teams'),
            ('google_meet', 'Google Meet'),
            ('other', 'Other'),
        ],
        required=True,
        default='other',
        tracking=True,
    )
    external_ref = fields.Char(help='Source provider meeting identifier.')
    meeting_datetime = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    team_id = fields.Many2one('crm.ai.agent.team', tracking=True)

    # CRM decoupling: Use Reference field
    opportunity_ref = fields.Reference(
        selection='_get_opportunity_models',
        string='Opportunity',
        tracking=True,
        help='Linked opportunity. Works with CRM or other sales modules.',
    )
    # Legacy field for backward compatibility
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity (Legacy)',
        compute='_compute_opportunity_id',
        inverse='_inverse_opportunity_id',
        store=True,
    )

    raw_transcript = fields.Text(required=True)
    language = fields.Char(default='en')
    ingest_status = fields.Selection(
        [('new', 'New'), ('processed', 'Processed'), ('failed', 'Failed')],
        default='new',
        required=True,
        index=True,
        tracking=True,
    )
    processing_error = fields.Text()
    summary_id = fields.Many2one('crm.ai.conversation.summary', readonly=True)

    # Vector embedding for transcript content
    embedding_vector = fields.Binary(
        attachment=True,
        string='Embedding Vector',
        help='Embedding vector for the transcript content.',
    )

    _sql_constraints = [
        (
            'provider_external_ref_uniq',
            'unique(provider, external_ref)',
            'Transcript already imported for this provider/external reference.',
        )
    ]

    @api.model
    def _get_opportunity_models(self):
        """Get available opportunity models based on installed modules."""
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    @api.depends('opportunity_ref')
    def _compute_opportunity_id(self):
        for record in self:
            if record.opportunity_ref and record.opportunity_ref._name == 'crm.lead':
                record.opportunity_id = record.opportunity_ref.id
            else:
                record.opportunity_id = False

    def _inverse_opportunity_id(self):
        for record in self:
            if record.opportunity_id:
                record.opportunity_ref = f'crm.lead,{record.opportunity_id.id}'
            else:
                record.opportunity_ref = False

    def action_process_transcript(self):
        for transcript in self:
            try:
                transcript._create_or_update_summary_from_transcript()
                transcript.write({'ingest_status': 'processed', 'processing_error': False})
            except Exception as err:  # noqa: BLE001
                transcript.write({'ingest_status': 'failed', 'processing_error': str(err)})
        return True

    def _create_or_update_summary_from_transcript(self):
        self.ensure_one()
        sentiment = self._infer_sentiment()
        theme_codes = self._infer_theme_codes()
        summary_text, key_points = self._extract_summary_sections()

        values = {
            'name': self.name,
            'conversation_datetime': self.meeting_datetime,
            'team_id': self.team_id.id,
            'partner_id': self.partner_id.id,
            'opportunity_ref': f'{self.opportunity_ref._name},{self.opportunity_ref.id}' if self.opportunity_ref else False,
            'sentiment': sentiment,
            'summary': summary_text,
            'key_points': key_points,
            'transcript_id': self.id,
            'processed': False,
        }
        if self.summary_id:
            self.summary_id.write(values)
            summary = self.summary_id
        else:
            summary = self.env['crm.ai.conversation.summary'].create(values)
        theme_ids = self.env['crm.ai.theme'].search([('code', 'in', theme_codes)]).ids
        if theme_ids:
            summary.theme_ids = [(6, 0, theme_ids)]
        self.summary_id = summary.id
        return summary

    def _infer_sentiment(self):
        self.ensure_one()
        text = (self.raw_transcript or '').lower()
        negative_terms = ('cancel', 'churn', 'issue', 'problem', 'frustrated', 'unhappy', 'downtime')
        positive_terms = ('great', 'happy', 'excited', 'successful', 'value', 'thank you', 'improved')
        neg_hits = sum(1 for term in negative_terms if term in text)
        pos_hits = sum(1 for term in positive_terms if term in text)
        if neg_hits >= 3:
            return 'very_negative'
        if neg_hits > pos_hits:
            return 'negative'
        if pos_hits >= 3:
            return 'very_positive'
        if pos_hits > neg_hits:
            return 'positive'
        return 'neutral'

    def _infer_theme_codes(self):
        self.ensure_one()
        text = (self.raw_transcript or '').lower()
        themes = {'general'}
        mapping = {
            'cross_sell': ('cross-sell', 'cross sell', 'adjacent product', 'add-on'),
            'upsell': ('upgrade', 'upsell', 'enterprise plan', 'higher tier'),
            'renewal': ('renewal', 'renew', 'contract term', 'expiration'),
            'churn_risk': ('cancel', 'churn', 'switch provider', 'at risk'),
            'support_case': ('ticket', 'bug', 'incident', 'support case'),
            'product_feedback': ('feedback', 'feature request', 'roadmap'),
        }
        for code, terms in mapping.items():
            if any(term in text for term in terms):
                themes.add(code)
        return list(themes)

    def _extract_summary_sections(self):
        self.ensure_one()
        lines = [line.strip() for line in (self.raw_transcript or '').splitlines() if line.strip()]
        summary_lines = lines[:6]
        key_lines = lines[:10]
        summary = ' '.join(summary_lines) if summary_lines else self.name
        key_points = '\n'.join(f'- {line}' for line in key_lines) if key_lines else '- No key points extracted'
        return summary, key_points


class CrmAiRelationshipSignal(models.Model):
    """Actionable signal from AI analysis.

    Signals are recommendations for action based on conversation analysis,
    including cross-sell, upsell, renewal, and churn risk indicators.
    """
    _name = 'crm.ai.relationship.signal'
    _description = 'AI Relationship Signal'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    summary_id = fields.Many2one(
        'crm.ai.conversation.summary', required=True, ondelete='cascade', index=True
    )
    partner_id = fields.Many2one('res.partner', related='summary_id.partner_id', store=True)
    signal_type = fields.Selection(
        [
            ('cross_sell', 'Cross-sell Opportunity'),
            ('upsell', 'Upsell Opportunity'),
            ('renewal', 'Renewal Action'),
            ('churn_risk', 'Churn Risk'),
        ],
        required=True,
        tracking=True,
    )
    confidence = fields.Float(help='Model confidence score from 0 to 1.')
    priority = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium',
        required=True,
        tracking=True,
    )
    recommendation = fields.Text(required=True)
    owner_id = fields.Many2one('res.users', string='Owner', tracking=True)

    # CRM decoupling: Use Reference field
    lead_ref = fields.Reference(
        selection='_get_lead_models',
        string='Related Opportunity',
        tracking=True,
    )
    # Legacy field
    lead_id = fields.Many2one(
        'crm.lead',
        string='Related Opportunity (Legacy)',
        compute='_compute_lead_id',
        inverse='_inverse_lead_id',
        store=True,
    )

    case_ref = fields.Reference(selection='_referenceable_models', string='Related Case')

    # Signal lifecycle
    state = fields.Selection(
        [
            ('new', 'New'),
            ('acknowledged', 'Acknowledged'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
            ('dismissed', 'Dismissed'),
        ],
        default='new',
        required=True,
        tracking=True,
        index=True,
    )
    resolution_notes = fields.Text(tracking=True)

    @api.model
    def _get_lead_models(self):
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    @api.model
    def _referenceable_models(self):
        return self.env['crm.ai.conversation.summary']._referenceable_models()

    @api.depends('lead_ref')
    def _compute_lead_id(self):
        for record in self:
            if record.lead_ref and record.lead_ref._name == 'crm.lead':
                record.lead_id = record.lead_ref.id
            else:
                record.lead_id = False

    def _inverse_lead_id(self):
        for record in self:
            if record.lead_id:
                record.lead_ref = f'crm.lead,{record.lead_id.id}'
            else:
                record.lead_ref = False

    def action_acknowledge(self):
        self.write({'state': 'acknowledged'})
        return True

    def action_start_progress(self):
        self.write({'state': 'in_progress'})
        return True

    def action_resolve(self):
        self.write({'state': 'resolved'})
        return True

    def action_dismiss(self):
        self.write({'state': 'dismissed'})
        return True

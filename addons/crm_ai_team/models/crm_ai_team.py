import random

from odoo import api, fields, models


class CrmAiAgentTeam(models.Model):
    _name = 'crm.ai.agent.team'
    _description = 'AI Agent Team'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    member_ids = fields.One2many('crm.ai.agent', 'team_id', string='Agents')
    summary_ids = fields.One2many('crm.ai.conversation.summary', 'team_id', string='Conversation Summaries')
    run_ids = fields.One2many('crm.ai.agent.run', 'team_id', string='Agent Runs')
    run_count = fields.Integer(compute='_compute_run_metrics')
    last_run_date = fields.Datetime(compute='_compute_run_metrics')
    last_run_status = fields.Selection(
        [('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')],
        compute='_compute_run_metrics',
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

        for index in range(transcript_count):
            partner = self.env['res.partner'].create({'name': f'{team_name} Customer {index + 1}'})
            opportunity = self.env['crm.lead'].create(
                {
                    'name': f'{team_name} Opportunity {index + 1}',
                    'type': 'opportunity',
                    'partner_id': partner.id,
                    'expected_revenue': 1000 + rng.randint(0, 20000),
                }
            )
            sentence = transcript_templates[index % len(transcript_templates)]
            transcript = self.env['crm.ai.meeting.transcript'].create(
                {
                    'name': f'{team_name} Meeting {index + 1}',
                    'provider': providers[index % len(providers)],
                    'external_ref': f'{team.id}-{index + 1}',
                    'partner_id': partner.id,
                    'team_id': team.id,
                    'opportunity_id': opportunity.id,
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
    _name = 'crm.ai.agent'
    _description = 'AI Agent Profile'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    team_id = fields.Many2one('crm.ai.agent.team', required=True, ondelete='cascade')
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
    )
    instruction = fields.Text(
        help='Prompt or policy used by this agent when participating in an orchestration flow.'
    )


class CrmAiTheme(models.Model):
    _name = 'crm.ai.theme'
    _description = 'AI Conversation Theme'

    name = fields.Char(required=True)
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
    )
    description = fields.Text()


class CrmAiConversationSummary(models.Model):
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
    opportunity_id = fields.Many2one('crm.lead', string='Sales Opportunity')
    case_ref = fields.Reference(
        selection='_referenceable_models',
        string='Case',
        help='Optional case/ticket linked to this summary.',
    )
    signal_ids = fields.One2many('crm.ai.relationship.signal', 'summary_id', string='Relationship Signals')
    transcript_id = fields.Many2one('crm.ai.meeting.transcript', string='Source Transcript', index=True)
    processed = fields.Boolean(default=False, tracking=True)

    @api.model
    def _referenceable_models(self):
        model_names = ['helpdesk.ticket', 'project.task', 'crm.lead']
        models = self.env['ir.model'].sudo().search([('model', 'in', model_names)])
        return [(model.model, model.name) for model in models]

    def _apply_agent_logic(self, agent):
        self.ensure_one()
        signal_vals = self._build_signal_vals(agent)
        if signal_vals:
            self.env['crm.ai.relationship.signal'].create(signal_vals)
            return f"Created signal '{signal_vals['signal_type']}' for summary '{self.name}'."
        return f"No signal created for summary '{self.name}' by agent '{agent.name}'."

    def _build_signal_vals(self, agent):
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

        return {
            'summary_id': self.id,
            'signal_type': signal_type,
            'priority': priority,
            'confidence': confidence,
            'recommendation': recommendation,
            'lead_id': self.opportunity_id.id,
            'owner_id': self.env.user.id,
        }


class CrmAiAgentRun(models.Model):
    _name = 'crm.ai.agent.run'
    _description = 'AI Agent Team Run'
    _order = 'start_datetime desc, id desc'

    name = fields.Char(required=True)
    team_id = fields.Many2one('crm.ai.agent.team', required=True, ondelete='cascade', index=True)
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime()
    status = fields.Selection(
        [('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')],
        default='success',
        required=True,
        index=True,
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


class CrmAiMeetingTranscript(models.Model):
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
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', tracking=True)
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

    _sql_constraints = [
        (
            'provider_external_ref_uniq',
            'unique(provider, external_ref)',
            'Transcript already imported for this provider/external reference.',
        )
    ]

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
            'opportunity_id': self.opportunity_id.id,
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
    _name = 'crm.ai.relationship.signal'
    _description = 'AI Relationship Signal'

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
    )
    confidence = fields.Float(help='Model confidence score from 0 to 1.')
    priority = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium',
        required=True,
    )
    recommendation = fields.Text(required=True)
    owner_id = fields.Many2one('res.users', string='Owner')
    lead_id = fields.Many2one('crm.lead', string='Related Opportunity')
    case_ref = fields.Reference(selection='_referenceable_models', string='Related Case')

    @api.model
    def _referenceable_models(self):
        return self.env['crm.ai.conversation.summary']._referenceable_models()

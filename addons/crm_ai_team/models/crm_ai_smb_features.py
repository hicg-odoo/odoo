"""
CRM AI Team - SMB Opinionated Features Module

This module implements the "Opinionated AI CRM" vision for SMBs:
- Renewal Engine: T-30/60/90 automated workflows
- Deal Health Intelligence: Multi-threading, velocity, decision-maker detection
- Sales Playbooks: Agent Operating Procedures (AOPs)
- Auto-Activity Generation: Extract action items from conversations
- Next Best Action: AI-prescribed recommendations
- Proactive Outbound: Stale lead re-engagement
- Lighthouse Beta: 7-day sandboxed trial program

Based on research from decagon.ai, Gong, and SMB CRM needs analysis.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils


# =============================================================================
# RENEWAL ENGINE - T-30/60/90 AUTOMATED WORKFLOWS
# =============================================================================

class CrmAiRenewalTracker(models.Model):
    """Renewal Tracker - Automated renewal management for SMBs.

    Provides prescriptive workflows for contract renewals:
    - T-90 days: Strategic review
    - T-60 days: Health check and engagement
    - T-30 days: Renewal execution
    - T-7 days: Final confirmation

    This is an "opinionated" feature - it tells users what to do,
    not just showing data.
    """
    _name = 'crm.ai.renewal.tracker'
    _description = 'Renewal Tracker'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'renewal_date asc, id asc'

    name = fields.Char(
        string='Tracker Name',
        compute='_compute_name',
        store=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        index=True,
    )

    # Contract Details
    contract_start = fields.Date(
        string='Contract Start',
        required=True,
        tracking=True,
    )
    contract_end = fields.Date(
        string='Contract End',
        required=True,
        tracking=True,
    )
    renewal_date = fields.Date(
        string='Renewal Date',
        compute='_compute_renewal_date',
        store=True,
        help='Date when renewal process should begin (90 days before contract end)',
    )
    contract_value = fields.Float(
        string='Contract Value',
        tracking=True,
        help='Annual contract value',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
    )

    # Renewal Phase Tracking
    phase = fields.Selection(
        [
            ('onboarding', 'Onboarding'),
            ('active', 'Active'),
            ('t90', 'T-90 Days (Strategic Review)'),
            ('t60', 'T-60 Days (Health Check)'),
            ('t30', 'T-30 Days (Execution)'),
            ('t7', 'T-7 Days (Final)'),
            ('renewed', 'Renewed'),
            ('churned', 'Churned'),
            ('expired', 'Expired'),
        ],
        default='onboarding',
        required=True,
        tracking=True,
        index=True,
    )
    phase_updated = fields.Datetime(
        string='Phase Updated',
        default=fields.Datetime.now,
    )

    # Risk Assessment
    risk_level = fields.Selection(
        [
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('critical', 'Critical Risk'),
        ],
        default='low',
        tracking=True,
        compute='_compute_risk_level',
        store=True,
    )
    risk_factors = fields.Text(
        string='Risk Factors (JSON)',
        help='JSON array of identified risk factors',
    )

    # Health Metrics
    health_score = fields.Integer(
        string='Health Score',
        default=70,
        tracking=True,
        help='Composite health score (0-100)',
    )
    engagement_score = fields.Integer(
        string='Engagement Score',
        default=70,
        help='Login frequency, feature usage',
    )
    support_score = fields.Integer(
        string='Support Score',
        default=70,
        help='Based on ticket volume and satisfaction',
    )
    nps_score = fields.Integer(
        string='NPS Score',
        help='Net Promoter Score from surveys',
    )
    sentiment_score = fields.Integer(
        string='Sentiment Score',
        default=70,
        help='From conversation analysis',
    )

    # Renewal Details
    renewal_opportunity_ref = fields.Reference(
        selection='_get_opportunity_models',
        string='Renewal Opportunity',
    )
    renewal_value = fields.Float(
        string='Renewal Value',
        help='Proposed renewal value',
    )
    upsell_potential = fields.Float(
        string='Upsell Potential',
        help='Identified upsell opportunity value',
    )

    # Account Manager
    owner_id = fields.Many2one(
        'res.users',
        string='Account Manager',
        tracking=True,
    )

    # AI Prescriptions
    next_best_action = fields.Text(
        string='Next Best Action',
        compute='_compute_next_best_action',
        help='AI-prescribed action for the account manager',
    )
    action_completed = fields.Boolean(
        string='Action Completed',
        default=False,
    )

    # Communication Tracking
    last_contact_date = fields.Date(
        string='Last Contact',
        compute='_compute_contact_metrics',
        store=True,
    )
    days_since_contact = fields.Integer(
        string='Days Since Contact',
        compute='_compute_contact_metrics',
        store=True,
    )

    # Playbook
    playbook_id = fields.Many2one(
        'crm.ai.sales.playbook',
        string='Active Playbook',
    )

    @api.model
    def _get_opportunity_models(self):
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    @api.depends('partner_id', 'contract_end')
    def _compute_name(self):
        for record in self:
            record.name = f"Renewal: {record.partner_id.name or 'Unknown'} - {record.contract_end or 'TBD'}"

    @api.depends('contract_end')
    def _compute_renewal_date(self):
        """Renewal process starts 90 days before contract end."""
        for record in self:
            if record.contract_end:
                record.renewal_date = record.contract_end - timedelta(days=90)
            else:
                record.renewal_date = False

    @api.depends(
        'engagement_score', 'support_score', 'nps_score', 'sentiment_score',
        'days_since_contact'
    )
    def _compute_risk_level(self):
        """Calculate risk level based on composite metrics."""
        for record in self:
            # Weighted health calculation
            total_score = (
                record.engagement_score * 0.30 +
                record.support_score * 0.25 +
                (record.nps_score + 100) / 2 * 0.20 +  # Normalize NPS (-100 to 100)
                record.sentiment_score * 0.15 +
                max(0, 100 - (record.days_since_contact or 0) * 2) * 0.10
            )
            record.health_score = int(total_score)

            # Risk classification
            if total_score >= 80:
                record.risk_level = 'low'
            elif total_score >= 60:
                record.risk_level = 'medium'
            elif total_score >= 40:
                record.risk_level = 'high'
            else:
                record.risk_level = 'critical'

    @api.depends('phase', 'risk_level', 'days_since_contact', 'upsell_potential')
    def _compute_next_best_action(self):
        """AI-prescribed next best action based on phase and risk.

        This is the core "opinionated" feature - it tells users
        exactly what to do next.
        """
        actions = {
            'onboarding': {
                'low': "Welcome call scheduled. Focus on product adoption.",
                'medium': "Schedule onboarding check-in within 7 days.",
                'high': "Urgent: Assign dedicated success manager.",
                'critical': "Escalate to leadership immediately.",
            },
            't90': {
                'low': "Send strategic review agenda. Discuss expansion goals.",
                'medium': "Schedule EBR (Executive Business Review). Review success metrics.",
                'high': "Request executive sponsorship meeting. Identify blockers.",
                'critical': "Escalate: Schedule urgent health assessment call.",
            },
            't60': {
                'low': "Send renewal proposal draft. Highlight ROI achieved.",
                'medium': "Confirm renewal intent. Address any concerns proactively.",
                'high': "Prepare contingency plan. Schedule risk mitigation call.",
                'critical': "Engage leadership: Personal outreach from executive.",
            },
            't30': {
                'low': "Finalize renewal contract. Process paperwork.",
                'medium': "Confirm renewal terms. Negotiate any adjustments.",
                'high': "Last chance: Offer retention incentives. Executive involvement required.",
                'critical': "All hands on deck: Maximum intervention required.",
            },
            't7': {
                'low': "Confirm contract signature. Process renewal.",
                'medium': "Final confirmation call. Address any last concerns.",
                'high': "Emergency retention offer. Direct executive negotiation.",
                'critical': "Accept potential churn. Document lessons learned.",
            },
        }

        for record in self:
            phase_actions = actions.get(record.phase, {})
            base_action = phase_actions.get(record.risk_level, "Review account status.")

            # Add upsell context if applicable
            if record.upsell_potential and record.upsell_potential > 0:
                base_action += f" Upsell opportunity identified: ${record.upsell_potential:,.0f}."

            # Add stale contact warning
            if record.days_since_contact and record.days_since_contact > 14:
                base_action += f" WARNING: No contact in {record.days_since_contact} days."

            record.next_best_action = base_action

    @api.depends('partner_id')
    def _compute_contact_metrics(self):
        """Calculate contact recency."""
        for record in self:
            if record.partner_id:
                # Find last activity/meeting with this partner
                activities = self.env['mail.activity'].search([
                    ('res_partner_id', '=', record.partner_id.id),
                ], order='write_date desc', limit=1)

                if activities:
                    last_date = activities.write_date.date()
                    record.last_contact_date = last_date
                    record.days_since_contact = (fields.Date.today() - last_date).days
                else:
                    record.last_contact_date = False
                    record.days_since_contact = 999
            else:
                record.last_contact_date = False
                record.days_since_contact = 0

    def action_update_phase(self):
        """Cron job to update renewal phases daily."""
        today = fields.Date.today()

        # Find trackers that need phase updates
        trackers = self.search([
            ('phase', 'not in', ['renewed', 'churned', 'expired']),
        ])

        for tracker in trackers:
            if not tracker.contract_end:
                continue

            days_to_renewal = (tracker.contract_end - today).days

            # Determine new phase
            if days_to_renewal <= 0:
                new_phase = 'expired'
            elif days_to_renewal <= 7:
                new_phase = 't7'
            elif days_to_renewal <= 30:
                new_phase = 't30'
            elif days_to_renewal <= 60:
                new_phase = 't60'
            elif days_to_renewal <= 90:
                new_phase = 't90'
            else:
                new_phase = 'active'

            if new_phase != tracker.phase:
                tracker.write({
                    'phase': new_phase,
                    'phase_updated': fields.Datetime.now(),
                })

                # Create activity for phase transition
                tracker._create_phase_activity(new_phase)

        return True

    def _create_phase_activity(self, new_phase):
        """Create activity when entering new phase."""
        self.ensure_one()

        phase_deadlines = {
            't90': 14,
            't60': 10,
            't30': 7,
            't7': 3,
        }

        deadline_days = phase_deadlines.get(new_phase, 7)

        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
            'res_partner_id': self.partner_id.id,
            'res_model_id': self.env.ref('crm_ai_team.model_crm_ai_renewal_tracker').id,
            'res_id': self.id,
            'user_id': self.owner_id.id or self.env.user.id,
            'date_deadline': fields.Date.today() + timedelta(days=deadline_days),
            'summary': f"Renewal Phase: {new_phase.replace('_', ' ').title()}",
            'note': self.next_best_action,
        })


# =============================================================================
# DEAL HEALTH INTELLIGENCE
# =============================================================================

class CrmAiDealHealth(models.Model):
    """Deal Health Intelligence - Monitor deal health and risks.

    Implements Gong-style signals for SMBs:
    - Multi-threading: Count of unique contacts
    - Velocity: Days since meaningful interaction
    - Decision-maker presence: Key stakeholders engaged
    - Competitor mentions: Risk indicators from conversations
    """
    _name = 'crm.ai.deal.health'
    _description = 'Deal Health Intelligence'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        compute='_compute_name',
        store=True,
    )
    opportunity_ref = fields.Reference(
        selection='_get_opportunity_models',
        string='Opportunity',
        required=True,
        index=True,
    )

    # Multi-threading Analysis
    contact_count = fields.Integer(
        string='Contacts Engaged',
        default=0,
        help='Number of unique contacts on the customer side',
    )
    is_single_threaded = fields.Boolean(
        string='Single-Threaded Risk',
        compute='_compute_threading_risk',
        store=True,
        help='True if only 1 contact (high risk)',
    )
    threading_score = fields.Integer(
        string='Threading Score',
        default=50,
        help='0-100 score based on contact diversity',
    )

    # Velocity Metrics
    days_since_last_activity = fields.Integer(
        string='Days Since Activity',
        default=0,
    )
    days_in_stage = fields.Integer(
        string='Days in Current Stage',
        default=0,
    )
    velocity_score = fields.Integer(
        string='Velocity Score',
        default=50,
        help='0-100 score based on deal momentum',
    )
    is_stale = fields.Boolean(
        string='Stale Deal',
        compute='_compute_velocity_risk',
        store=True,
        help='True if no activity in 14+ days',
    )

    # Decision Maker Detection
    decision_maker_engaged = fields.Boolean(
        string='Decision Maker Engaged',
        default=False,
        help='True if key stakeholder has participated',
    )
    decision_maker_mentions = fields.Integer(
        string='Decision Maker Mentions',
        default=0,
        help='Number of times decision maker was mentioned',
    )
    missing_stakeholder = fields.Boolean(
        string='Missing Key Stakeholder',
        compute='_compute_stakeholder_risk',
        store=True,
        help='True if deal mentions budget/legal/authority without contact',
    )

    # Competitor Intelligence
    competitor_mentions = fields.Integer(
        string='Competitor Mentions',
        default=0,
    )
    competitors_detected = fields.Text(
        string='Competitors Detected (JSON)',
        help='JSON array of competitor names mentioned',
    )
    competitor_risk = fields.Selection(
        [
            ('none', 'No Competitors'),
            ('low', 'Low - Casual Mention'),
            ('medium', 'Medium - Active Evaluation'),
            ('high', 'High - Strong Alternative'),
        ],
        default='none',
    )

    # Conversation Signals
    pricing_discussed = fields.Boolean(
        string='Pricing Discussed',
        default=False,
    )
    timeline_mentioned = fields.Boolean(
        string='Timeline Mentioned',
        default=False,
    )
    budget_confirmed = fields.Boolean(
        string='Budget Confirmed',
        default=False,
    )
    authority_present = fields.Boolean(
        string='Authority Present',
        default=False,
    )
    need_validated = fields.Boolean(
        string='Need Validated',
        default=False,
    )

    # BANT Score
    bant_score = fields.Integer(
        string='BANT Score',
        compute='_compute_bant_score',
        store=True,
        help='Budget + Authority + Need + Timeline score (0-100)',
    )

    # Overall Health
    overall_health = fields.Integer(
        string='Overall Deal Health',
        compute='_compute_overall_health',
        store=True,
    )
    health_category = fields.Selection(
        [
            ('healthy', 'Healthy (70-100)'),
            ('at_risk', 'At Risk (40-69)'),
            ('critical', 'Critical (0-39)'),
        ],
        compute='_compute_overall_health',
        store=True,
    )

    # AI Recommendations
    recommended_actions = fields.Text(
        string='Recommended Actions',
        compute='_compute_recommended_actions',
    )
    win_probability_adjustment = fields.Float(
        string='Win Probability Adjustment',
        default=0.0,
        help='Suggested adjustment to CRM probability field',
    )

    # Last Analysis
    last_analyzed = fields.Datetime(
        string='Last Analyzed',
        default=fields.Datetime.now,
    )

    @api.model
    def _get_opportunity_models(self):
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    @api.depends('opportunity_ref')
    def _compute_name(self):
        for record in self:
            if record.opportunity_ref:
                record.name = f"Health: {record.opportunity_ref.display_name}"
            else:
                record.name = "New Deal Health"

    @api.depends('contact_count')
    def _compute_threading_risk(self):
        """Calculate threading risk.

        Gong research: Deals with < 2 contacts have 25% lower win rate.
        """
        for record in self:
            record.is_single_threaded = record.contact_count < 2

            # Threading score: 1 contact = 25, 2 = 50, 3+ = 75, 5+ = 100
            if record.contact_count >= 5:
                record.threading_score = 100
            elif record.contact_count >= 3:
                record.threading_score = 75
            elif record.contact_count >= 2:
                record.threading_score = 50
            else:
                record.threading_score = 25

    @api.depends('days_since_last_activity', 'days_in_stage')
    def _compute_velocity_risk(self):
        """Calculate velocity risk.

        Deals stalling in stage > 30 days have 15% lower close rate.
        """
        for record in self:
            record.is_stale = record.days_since_last_activity > 14

            # Velocity score based on activity recency
            if record.days_since_last_activity <= 3:
                record.velocity_score = 100
            elif record.days_since_last_activity <= 7:
                record.velocity_score = 80
            elif record.days_since_last_activity <= 14:
                record.velocity_score = 60
            elif record.days_since_last_activity <= 21:
                record.velocity_score = 40
            else:
                record.velocity_score = 20

    @api.depends(
        'pricing_discussed', 'timeline_mentioned', 'budget_confirmed',
        'authority_present', 'need_validated'
    )
    def _compute_stakeholder_risk(self):
        """Detect if decision maker is missing.

        If budget/legal/boss mentioned but no stakeholder contact, flag risk.
        """
        for record in self:
            # Check if deal mentions authority keywords without contact
            mentions_need = (
                record.pricing_discussed or
                record.budget_confirmed or
                record.timeline_mentioned
            )
            record.missing_stakeholder = (
                mentions_need and
                not record.decision_maker_engaged and
                record.decision_maker_mentions == 0
            )

    @api.depends(
        'budget_confirmed', 'authority_present', 'need_validated', 'timeline_mentioned'
    )
    def _compute_bant_score(self):
        """Calculate BANT score.

        Budget (25%) + Authority (25%) + Need (25%) + Timeline (25%)
        """
        for record in self:
            score = 0
            if record.budget_confirmed:
                score += 25
            if record.authority_present:
                score += 25
            if record.need_validated:
                score += 25
            if record.timeline_mentioned:
                score += 25
            record.bant_score = score

    @api.depends(
        'threading_score', 'velocity_score', 'bant_score',
        'competitor_risk', 'missing_stakeholder'
    )
    def _compute_overall_health(self):
        """Calculate overall deal health.

        Weighted: Threading (25%) + Velocity (25%) + BANT (30%) + Competitor Risk (20%)
        """
        for record in self:
            # Competitor risk score (inverted)
            competitor_scores = {
                'none': 100,
                'low': 80,
                'medium': 50,
                'high': 20,
            }
            competitor_score = competitor_scores.get(record.competitor_risk, 100)

            # Missing stakeholder penalty
            stakeholder_penalty = 20 if record.missing_stakeholder else 0

            # Calculate weighted score
            total = (
                record.threading_score * 0.25 +
                record.velocity_score * 0.25 +
                record.bant_score * 0.30 +
                competitor_score * 0.20 -
                stakeholder_penalty
            )

            record.overall_health = max(0, min(100, int(total)))

            if record.overall_health >= 70:
                record.health_category = 'healthy'
            elif record.overall_health >= 40:
                record.health_category = 'at_risk'
            else:
                record.health_category = 'critical'

    def _compute_recommended_actions(self):
        """Generate AI-recommended actions based on health signals."""
        for record in self:
            actions = []

            if record.is_single_threaded:
                actions.append("CRITICAL: Single-threaded deal. Identify and engage additional stakeholders.")

            if record.is_stale:
                actions.append(f"URGENT: No activity in {record.days_since_last_activity} days. Re-engage immediately.")

            if record.missing_stakeholder:
                actions.append("Missing decision maker. Request introduction to budget authority.")

            if record.competitor_risk in ('high', 'medium'):
                actions.append("Competitor detected. Differentiate value proposition urgently.")

            if record.bant_score < 50:
                missing = []
                if not record.budget_confirmed:
                    missing.append("budget")
                if not record.authority_present:
                    missing.append("authority")
                if not record.need_validated:
                    missing.append("need validation")
                if not record.timeline_mentioned:
                    missing.append("timeline")
                actions.append(f"Missing BANT elements: {', '.join(missing)}")

            if not actions:
                actions.append("Deal is healthy. Continue current approach.")

            record.recommended_actions = "\n".join(f"{i+1}. {a}" for i, a in enumerate(actions))


# =============================================================================
# SALES PLAYBOOKS (AGENT OPERATING PROCEDURES)
# =============================================================================

class CrmAiSalesPlaybook(models.Model):
    """Sales Playbook - Agent Operating Procedures (AOP).

    Inspired by Decagon's AOP approach: Natural language instructions
    that define how AI agents should behave and respond.

    This allows SMBs to encode their sales process in plain English,
    making the CRM truly "opinionated" and prescriptive.
    """
    _name = 'crm.ai.sales.playbook'
    _description = 'Sales Playbook'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    name = fields.Char(
        string='Playbook Name',
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    description = fields.Text(
        tracking=True,
    )

    # Trigger Conditions
    trigger_type = fields.Selection(
        [
            ('manual', 'Manual Trigger'),
            ('new_lead', 'New Lead Created'),
            ('stage_change', 'Stage Changed'),
            ('stale_deal', 'Deal Stale (>14 days)'),
            ('competitor_mentioned', 'Competitor Mentioned'),
            ('renewal_t90', 'Renewal T-90'),
            ('renewal_t60', 'Renewal T-60'),
            ('renewal_t30', 'Renewal T-30'),
            ('high_risk', 'High Risk Detected'),
            ('upsell_signal', 'Upsell Signal Detected'),
        ],
        string='Trigger Type',
        required=True,
        default='manual',
        tracking=True,
    )
    trigger_stage_ids = fields.Many2many(
        'crm.stage',
        string='Trigger Stages',
        help='Stages that trigger this playbook (for stage_change trigger)',
    )

    # Target Audience
    target_audience = fields.Selection(
        [
            ('all', 'All Deals'),
            ('new_business', 'New Business'),
            ('renewal', 'Renewals'),
            ('upsell', 'Upsells'),
            ('at_risk', 'At Risk Deals'),
        ],
        default='all',
        string='Target Audience',
    )

    # Natural Language Instructions
    instructions = fields.Text(
        string='AI Instructions',
        required=True,
        tracking=True,
        help='Natural language instructions for the AI agent. Example: "When a lead mentions pricing, ask about their current provider and budget timeline."',
    )

    # Response Templates
    email_template = fields.Text(
        string='Email Template',
        help='Template with placeholders: {customer_name}, {company}, {last_interaction}, etc.',
    )
    call_script = fields.Text(
        string='Call Script',
        help='Talking points for phone conversations',
    )

    # Actions to Execute
    auto_create_activity = fields.Boolean(
        string='Auto-Create Activity',
        default=False,
        help='Automatically create follow-up activity when playbook triggers',
    )
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type',
    )
    activity_deadline_days = fields.Integer(
        string='Activity Deadline (Days)',
        default=7,
    )
    activity_summary = fields.Char(
        string='Activity Summary',
    )

    # Success Criteria
    success_criteria = fields.Text(
        string='Success Criteria',
        help='How to measure if playbook was successful (e.g., "Deal moved to next stage within 14 days")',
    )
    success_actions = fields.Text(
        string='On Success Actions',
        help='Actions to take when playbook succeeds',
    )
    failure_actions = fields.Text(
        string='On Failure Actions',
        help='Actions to take when playbook fails',
    )

    # Metrics
    times_triggered = fields.Integer(
        string='Times Triggered',
        default=0,
    )
    times_succeeded = fields.Integer(
        string='Times Succeeded',
        default=0,
    )
    success_rate = fields.Float(
        string='Success Rate',
        compute='_compute_success_rate',
        store=True,
    )

    @api.depends('times_triggered', 'times_succeeded')
    def _compute_success_rate(self):
        for record in self:
            if record.times_triggered > 0:
                record.success_rate = (record.times_succeeded / record.times_triggered) * 100
            else:
                record.success_rate = 0.0

    def action_trigger(self, record_ref):
        """Execute this playbook on a specific record.

        Args:
            record_ref: Reference to the record (e.g., 'crm.lead,42')
        """
        self.ensure_one()

        # Increment trigger count
        self.times_triggered += 1

        # Create activity if configured
        if self.auto_create_activity and self.activity_type_id:
            model_name, record_id = record_ref.split(',')
            self.env['mail.activity'].create({
                'activity_type_id': self.activity_type_id.id,
                'res_model': model_name,
                'res_id': int(record_id),
                'date_deadline': fields.Date.today() + timedelta(days=self.activity_deadline_days),
                'summary': self.activity_summary or f"Playbook: {self.name}",
                'note': self.instructions,
            })

        return True


# =============================================================================
# AUTO-ACTIVITY GENERATION
# =============================================================================

class CrmAiAutoActivity(models.Model):
    """Auto-Activity Generation - Extract action items from conversations.

    Automatically creates mail.activity records from:
    - Meeting transcripts
    - Email analysis
    - Conversation summaries
    """
    _name = 'crm.ai.auto.activity'
    _description = 'Auto-Activity Generator'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Source',
        required=True,
    )
    source_type = fields.Selection(
        [
            ('transcript', 'Meeting Transcript'),
            ('email', 'Email'),
            ('summary', 'Conversation Summary'),
            ('nl_query', 'Natural Language Query'),
        ],
        required=True,
    )
    source_ref = fields.Reference(
        selection='_get_source_models',
        string='Source Record',
    )

    # Extracted Action Items
    action_items = fields.Text(
        string='Action Items (JSON)',
        help='JSON array of extracted action items',
    )
    action_count = fields.Integer(
        string='Action Items Count',
        compute='_compute_action_count',
    )

    # Activities Created
    activity_ids = fields.One2many(
        'mail.activity',
        'auto_activity_id',
        string='Created Activities',
    )
    activity_count = fields.Integer(
        string='Activities Created',
        compute='_compute_activity_count',
    )

    # Status
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('processed', 'Processed'),
            ('reviewed', 'Reviewed'),
        ],
        default='pending',
        required=True,
    )

    @api.model
    def _get_source_models(self):
        return [
            ('crm.ai.meeting.transcript', 'Meeting Transcript'),
            ('crm.ai.email.intelligence', 'Email Intelligence'),
            ('crm.ai.conversation.summary', 'Conversation Summary'),
            ('crm.ai.nl.query', 'NL Query'),
        ]

    def _compute_action_count(self):
        for record in self:
            try:
                items = json.loads(record.action_items or '[]')
                record.action_count = len(items)
            except (json.JSONDecodeError, TypeError):
                record.action_count = 0

    def _compute_activity_count(self):
        for record in self:
            record.activity_count = len(record.activity_ids)

    def action_generate_activities(self):
        """Generate mail.activity records from extracted action items."""
        for record in self:
            if record.state != 'pending':
                continue

            try:
                items = json.loads(record.action_items or '[]')
            except (json.JSONDecodeError, TypeError):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                # Create activity
                activity_vals = {
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': item.get('title', item.get('action', 'Follow-up')),
                    'note': item.get('description', ''),
                    'date_deadline': fields.Date.today() + timedelta(days=item.get('days', 7)),
                    'auto_activity_id': record.id,
                }

                # Link to partner if available
                if record.source_ref and hasattr(record.source_ref, 'partner_id'):
                    activity_vals['res_partner_id'] = record.source_ref.partner_id.id

                self.env['mail.activity'].create(activity_vals)

            record.write({'state': 'processed'})


# =============================================================================
# NEXT BEST ACTION ENGINE
# =============================================================================

class CrmAiNextBestAction(models.Model):
    """Next Best Action Engine - AI-prescribed recommendations.

    Provides personalized, context-aware recommendations for:
    - Which customer to contact next
    - What to say (personalized talking points)
    - Which deals need attention
    """
    _name = 'crm.ai.next.best.action'
    _description = 'Next Best Action'
    _inherit = ['mail.thread']
    _order = 'priority desc, deadline asc, id asc'

    name = fields.Char(
        string='Action Title',
        required=True,
    )
    action_type = fields.Selection(
        [
            ('call', 'Phone Call'),
            ('email', 'Send Email'),
            ('meeting', 'Schedule Meeting'),
            ('follow_up', 'Follow Up'),
            ('review', 'Review Deal'),
            ('escalate', 'Escalate'),
            ('proposal', 'Send Proposal'),
            ('renewal', 'Renewal Action'),
        ],
        required=True,
        default='call',
    )

    # Context
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        index=True,
    )
    opportunity_ref = fields.Reference(
        selection='_get_opportunity_models',
        string='Opportunity',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        default=lambda self: self.env.user.id,
    )

    # Priority and Timing
    priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Medium'),
            ('2', 'High'),
            ('3', 'Urgent'),
        ],
        default='1',
        required=True,
        index=True,
    )
    deadline = fields.Date(
        string='Deadline',
        default=lambda self: fields.Date.today() + timedelta(days=3),
    )

    # AI-Generated Content
    reasoning = fields.Text(
        string='AI Reasoning',
        help='Why this action is recommended',
    )
    talking_points = fields.Text(
        string='Talking Points',
        help='AI-generated talking points for the interaction',
    )
    context_summary = fields.Text(
        string='Context Summary',
        help='Relevant context from previous interactions',
    )

    # Template Content
    suggested_email = fields.Text(
        string='Suggested Email',
        help='AI-drafted email template',
    )
    call_script = fields.Text(
        string='Call Script',
        help='Suggested script for phone calls',
    )

    # Execution Tracking
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('dismissed', 'Dismissed'),
            ('expired', 'Expired'),
        ],
        default='pending',
        required=True,
        tracking=True,
        index=True,
    )
    completed_date = fields.Datetime(
        string='Completed Date',
    )
    outcome = fields.Text(
        string='Outcome',
        help='Result of the action',
    )

    # Source
    source_type = fields.Selection(
        [
            ('renewal', 'Renewal Engine'),
            ('deal_health', 'Deal Health'),
            ('playbook', 'Sales Playbook'),
            ('stale', 'Stale Lead'),
            ('upsell', 'Upsell Signal'),
            ('churn_risk', 'Churn Risk'),
        ],
        string='Source',
    )

    @api.model
    def _get_opportunity_models(self):
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    def action_complete(self, outcome=''):
        """Mark action as completed."""
        for record in self:
            record.write({
                'state': 'completed',
                'completed_date': fields.Datetime.now(),
                'outcome': outcome,
            })
        return True

    def action_dismiss(self, reason=''):
        """Dismiss this action."""
        for record in self:
            record.write({
                'state': 'dismissed',
                'outcome': f"Dismissed: {reason}",
            })
        return True

    @api.model
    def action_generate_daily_recommendations(self):
        """Generate next best actions for all users.

        Called by daily cron job to populate each user's action queue.
        """
        users = self.env['res.users'].search([
            ('active', '=', True),
        ])

        for user in users:
            self._generate_user_recommendations(user)

        return True

    def _generate_user_recommendations(self, user):
        """Generate recommendations for a specific user."""
        # Get stale leads
        stale_threshold = fields.Date.today() - timedelta(days=14)

        # Find opportunities assigned to user with no recent activity
        if self.env.registry.get('crm.lead') is not None:
            opportunities = self.env['crm.lead'].search([
                ('user_id', '=', user.id),
                ('type', '=', 'opportunity'),
                ('active', '=', True),
            ])

            for opp in opportunities:
                # Check if already has pending action
                existing = self.search_count([
                    ('user_id', '=', user.id),
                    ('opportunity_ref', '=', f'crm.lead,{opp.id}'),
                    ('state', '=', 'pending'),
                ])

                if existing > 0:
                    continue

                # Get last activity date
                activities = self.env['mail.activity'].search([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', opp.id),
                ], order='write_date desc', limit=1)

                if activities:
                    last_activity = activities.write_date.date()
                else:
                    last_activity = opp.create_date.date()

                days_inactive = (fields.Date.today() - last_activity).days

                # Generate recommendation if stale
                if days_inactive > 7:
                    self.create({
                        'name': f"Re-engage: {opp.name}",
                        'action_type': 'call',
                        'partner_id': opp.partner_id.id,
                        'opportunity_ref': f'crm.lead,{opp.id}',
                        'user_id': user.id,
                        'priority': '2' if days_inactive > 14 else '1',
                        'deadline': fields.Date.today() + timedelta(days=3),
                        'reasoning': f"No activity in {days_inactive} days. Deal needs attention.",
                        'talking_points': f"Check in on {opp.name}. Discuss: {opp.name}",
                        'source_type': 'stale',
                    })


# =============================================================================
# PROACTIVE OUTBOUND - STALE LEAD RE-ENGAGEMENT
# =============================================================================

class CrmAiProactiveOutbound(models.Model):
    """Proactive Outbound - AI-drafted re-engagement campaigns.

    Automatically drafts (but doesn't send) personalized emails for:
    - Stale leads (>10 days in 'New')
    - Opportunities needing attention
    - Renewal reminders
    """
    _name = 'crm.ai.proactive.outbound'
    _description = 'Proactive Outbound Draft'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Draft Name',
        required=True,
    )
    outbound_type = fields.Selection(
        [
            ('re_engagement', 'Re-engagement'),
            ('renewal_reminder', 'Renewal Reminder'),
            ('upsell_nudge', 'Upsell Nudge'),
            ('check_in', 'Check-in'),
            ('value_delivery', 'Value Delivery'),
        ],
        required=True,
        default='check_in',
    )

    # Target
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
    )
    opportunity_ref = fields.Reference(
        selection='_get_opportunity_models',
        string='Opportunity',
    )

    # Generated Content
    subject = fields.Char(
        string='Email Subject',
        required=True,
    )
    body = fields.Html(
        string='Email Body',
        required=True,
    )

    # Personalization Context
    personalization_data = fields.Text(
        string='Personalization Data (JSON)',
        help='Data used for personalization: last_interaction, key_topics, etc.',
    )

    # Approval & Sending
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending_approval', 'Pending Approval'),
            ('approved', 'Approved'),
            ('sent', 'Sent'),
            ('dismissed', 'Dismissed'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
    )
    sent_date = fields.Datetime(
        string='Sent Date',
    )

    # Response Tracking
    opened = fields.Boolean(
        string='Opened',
        default=False,
    )
    clicked = fields.Boolean(
        string='Clicked',
        default=False,
    )
    replied = fields.Boolean(
        string='Replied',
        default=False,
    )

    @api.model
    def _get_opportunity_models(self):
        models = []
        if self.env.registry.get('crm.lead') is not None:
            models.append(('crm.lead', 'CRM Opportunity'))
        return models

    def action_submit_for_approval(self):
        """Submit draft for manager approval."""
        self.write({'state': 'pending_approval'})
        return True

    def action_approve(self):
        """Approve the draft for sending."""
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
        })
        return True

    def action_send(self):
        """Send the email (after approval)."""
        for record in self:
            if record.state != 'approved':
                continue

            # Create and send email
            mail_vals = {
                'subject': record.subject,
                'body_html': record.body,
                'email_to': record.partner_id.email,
                'auto_delete': False,
            }

            mail = self.env['mail.mail'].create(mail_vals)
            mail.send()

            record.write({
                'state': 'sent',
                'sent_date': fields.Datetime.now(),
            })

        return True

    def action_dismiss(self):
        """Dismiss this draft."""
        self.write({'state': 'dismissed'})
        return True

    @api.model
    def action_generate_stale_lead_drafts(self):
        """Generate drafts for stale leads.

        Called by cron job daily.
        """
        stale_threshold = fields.Date.today() - timedelta(days=10)

        if self.env.registry.get('crm.lead') is not None:
            # Find leads in 'New' stage for > 10 days
            new_stage = self.env['crm.stage'].search([
                ('name', 'ilike', 'new'),
            ], limit=1)

            if new_stage:
                stale_leads = self.env['crm.lead'].search([
                    ('stage_id', '=', new_stage.id),
                    ('type', '=', 'lead'),
                    ('create_date', '<=', stale_threshold),
                    ('active', '=', True),
                ])

                for lead in stale_leads:
                    # Check if draft already exists
                    existing = self.search_count([
                        ('partner_id', '=', lead.partner_id.id),
                        ('outbound_type', '=', 're_engagement'),
                        ('state', 'in', ['draft', 'pending_approval', 'approved']),
                    ])

                    if existing > 0:
                        continue

                    # Generate re-engagement draft
                    self.create({
                        'name': f"Re-engage: {lead.name}",
                        'outbound_type': 're_engagement',
                        'partner_id': lead.partner_id.id,
                        'opportunity_ref': f'crm.lead,{lead.id}',
                        'subject': f"Following up on your interest in {lead.company_id.name or 'our services'}",
                        'body': self._generate_re_engagement_body(lead),
                        'state': 'draft',
                    })

        return True

    def _generate_re_engagement_body(self, lead):
        """Generate personalized re-engagement email body."""
        partner = lead.partner_id
        company = lead.company_id

        body = f"""
        <p>Hi {partner.name or 'there'},</p>

        <p>I noticed we connected about {lead.name} a while back, and I wanted to follow up.</p>

        <p>I understand things get busy, but I wanted to make sure we didn't lose touch.
        We've helped companies like yours achieve significant results, and I'd love to
        explore how we might be able to help {company.name if company else 'your team'}.</p>

        <p>Would you be open to a quick 15-minute call this week to see if there's still
        a fit?</p>

        <p>Looking forward to hearing from you.</p>

        <p>Best regards,<br>
        {self.env.user.name}</p>
        """

        return body


# =============================================================================
# LIGHTHOUSE BETA PROGRAM
# =============================================================================

class CrmAiLighthouseBeta(models.Model):
    """Lighthouse Beta Program - 7-day sandboxed trial.

    Provides a risk-free way for SMBs to evaluate the AI CRM:
    - Sandboxed environment (no real data)
    - Synthetic demo data
    - Guided "jobs to be done" tours
    - Success metrics tracking
    """
    _name = 'crm.ai.lighthouse.beta'
    _description = 'Lighthouse Beta Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(
        string='Program Name',
        required=True,
    )
    company_name = fields.Char(
        string='Company',
        required=True,
        tracking=True,
    )
    contact_name = fields.Char(
        string='Contact Name',
        tracking=True,
    )
    contact_email = fields.Char(
        string='Contact Email',
        tracking=True,
    )

    # Trial Configuration
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.today,
        required=True,
    )
    end_date = fields.Date(
        string='End Date',
        compute='_compute_end_date',
        store=True,
    )
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_days_remaining',
    )

    # Status
    state = fields.Selection(
        [
            ('invited', 'Invited'),
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('converted', 'Converted'),
            ('expired', 'Expired'),
        ],
        default='invited',
        required=True,
        tracking=True,
    )

    # Demo Data
    demo_partner_id = fields.Many2one(
        'res.partner',
        string='Demo Customer',
        help='Synthetic customer created for this beta',
    )
    demo_team_id = fields.Many2one(
        'crm.ai.agent.team',
        string='Demo Team',
        help='Demo AI team for this beta',
    )

    # Jobs to be Done Tracking
    job_ids = fields.One2many(
        'crm.ai.lighthouse.job',
        'beta_id',
        string='Jobs to be Done',
    )
    jobs_completed = fields.Integer(
        string='Jobs Completed',
        compute='_compute_jobs_progress',
    )
    jobs_total = fields.Integer(
        string='Total Jobs',
        compute='_compute_jobs_progress',
    )
    completion_percentage = fields.Float(
        string='Completion %',
        compute='_compute_jobs_progress',
    )

    # Success Metrics
    time_saved_hours = fields.Float(
        string='Time Saved (Hours)',
        default=0.0,
        help='Estimated hours saved during trial',
    )
    activities_automated = fields.Integer(
        string='Activities Automated',
        default=0,
    )
    insights_generated = fields.Integer(
        string='Insights Generated',
        default=0,
    )

    # Conversion
    conversion_intent = fields.Selection(
        [
            ('none', 'No Response'),
            ('interested', 'Interested'),
            ('demo_requested', 'Demo Requested'),
            ('pricing_requested', 'Pricing Requested'),
            ('not_interested', 'Not Interested'),
        ],
        default='none',
        tracking=True,
    )
    feedback = fields.Text(
        string='Feedback',
    )
    testimonial_quote = fields.Text(
        string='Testimonial Quote',
        help='Customer quote for marketing use',
    )

    @api.depends('start_date')
    def _compute_end_date(self):
        """Lighthouse program runs for 7 days."""
        for record in self:
            if record.start_date:
                record.end_date = record.start_date + timedelta(days=7)
            else:
                record.end_date = False

    @api.depends('end_date')
    def _compute_days_remaining(self):
        for record in self:
            if record.end_date:
                remaining = (record.end_date - fields.Date.today()).days
                record.days_remaining = max(0, remaining)
            else:
                record.days_remaining = 0

    def _compute_jobs_progress(self):
        for record in self:
            jobs = record.job_ids
            record.jobs_total = len(jobs)
            record.jobs_completed = len([j for j in jobs if j.state == 'completed'])
            if record.jobs_total > 0:
                record.completion_percentage = (record.jobs_completed / record.jobs_total) * 100
            else:
                record.completion_percentage = 0.0

    def action_activate(self):
        """Activate the beta program."""
        for beta in self:
            # Create demo data
            beta._create_demo_data()

            # Create jobs to be done
            beta._create_jobs()

            beta.write({'state': 'active'})

        return True

    def _create_demo_data(self):
        """Create synthetic demo data for this beta."""
        # Create demo customer
        partner = self.env['res.partner'].create({
            'name': f"Demo Customer - {self.company_name}",
            'email': f"demo@{self.company_name.lower().replace(' ', '')}.com",
            'is_company': True,
        })

        # Create demo team
        team = self.env['crm.ai.agent.team'].create({
            'name': f"Beta Team - {self.company_name}",
            'llm_provider': 'none',  # Rule-based for demo
        })

        self.write({
            'demo_partner_id': partner.id,
            'demo_team_id': team.id,
        })

    def _create_jobs(self):
        """Create guided jobs to be done for this beta."""
        jobs = [
            {
                'name': 'View AI Conversation Summary',
                'description': 'See how AI automatically summarizes customer conversations',
                'sequence': 1,
            },
            {
                'name': 'Review Relationship Signals',
                'description': 'Discover how AI identifies upsell, renewal, and churn risk signals',
                'sequence': 2,
            },
            {
                'name': 'Check Customer Health Score',
                'description': 'Understand your customer health dashboard',
                'sequence': 3,
            },
            {
                'name': 'Test Natural Language Query',
                'description': 'Ask a question in plain English about your CRM data',
                'sequence': 4,
            },
            {
                'name': 'Review Next Best Actions',
                'description': 'See AI-recommended actions for your accounts',
                'sequence': 5,
            },
        ]

        for job_data in jobs:
            self.env['crm.ai.lighthouse.job'].create({
                'beta_id': self.id,
                'name': job_data['name'],
                'description': job_data['description'],
                'sequence': job_data['sequence'],
            })

    def action_convert(self):
        """Convert beta to full subscription."""
        self.write({'state': 'converted'})
        return True


class CrmAiLighthouseJob(models.Model):
    """Lighthouse Beta Job - Guided task for beta users."""
    _name = 'crm.ai.lighthouse.job'
    _description = 'Lighthouse Beta Job'
    _order = 'sequence, id'

    beta_id = fields.Many2one(
        'crm.ai.lighthouse.beta',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(
        required=True,
    )
    description = fields.Text()
    sequence = fields.Integer(
        default=10,
    )
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        default='pending',
        required=True,
    )
    completed_date = fields.Datetime(
        string='Completed Date',
    )
    notes = fields.Text()

    def action_start(self):
        self.write({'state': 'in_progress'})
        return True

    def action_complete(self, notes=''):
        self.write({
            'state': 'completed',
            'completed_date': fields.Datetime.now(),
            'notes': notes,
        })
        return True


# =============================================================================
# INTEGRATION HOOKS
# =============================================================================

# Add relationship to existing models
class MailActivity(models.Model):
    """Extend mail.activity to track auto-generation."""
    _inherit = 'mail.activity'

    auto_activity_id = fields.Many2one(
        'crm.ai.auto.activity',
        string='Auto-Generated From',
    )

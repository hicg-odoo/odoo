from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCrmAiAgentLoops(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env['crm.ai.agent.team'].create({'name': 'QA Team'})
        cls.sales_agent = cls.env['crm.ai.agent'].create(
            {
                'name': 'Sales Bot',
                'team_id': cls.team.id,
                'role': 'sales_specialist',
            }
        )
        cls.renewal_agent = cls.env['crm.ai.agent'].create(
            {
                'name': 'Renewal Bot',
                'team_id': cls.team.id,
                'role': 'renewal_specialist',
            }
        )
        cls.partner = cls.env['res.partner'].create({'name': 'QA Customer'})
        cls.opportunity = cls.env['crm.lead'].create(
            {
                'name': 'QA Opportunity',
                'type': 'opportunity',
                'partner_id': cls.partner.id,
            }
        )
        cls.theme_renewal = cls.env['crm.ai.theme'].create({'name': 'Renewal', 'code': 'renewal'})
        cls.theme_upsell = cls.env['crm.ai.theme'].create({'name': 'Upsell', 'code': 'upsell'})

    def test_run_pipeline_marks_processed_and_creates_logs(self):
        summary = self.env['crm.ai.conversation.summary'].create(
            {
                'name': 'Summary 1',
                'team_id': self.team.id,
                'partner_id': self.partner.id,
                'opportunity_id': self.opportunity.id,
                'sentiment': 'neutral',
                'summary': 'Customer discussed renewal and possible upgrade.',
                'theme_ids': [(6, 0, [self.theme_renewal.id, self.theme_upsell.id])],
            }
        )

        self.team.action_run_agent_team()

        summary.invalidate_recordset(['processed'])
        self.assertTrue(summary.processed)
        run = self.env['crm.ai.agent.run'].search([('team_id', '=', self.team.id)], order='id desc', limit=1)
        self.assertTrue(run)
        self.assertEqual(run.processed_summary_count, 1)
        self.assertEqual(run.failed_step_count, 0)
        self.assertEqual(run.success_step_count, len(self.team.member_ids))
        logs = self.env['crm.ai.agent.run.log'].search([('run_id', '=', run.id)])
        self.assertEqual(len(logs), len(self.team.member_ids))

    def test_negative_sentiment_creates_churn_risk_signal(self):
        summary = self.env['crm.ai.conversation.summary'].create(
            {
                'name': 'Summary 2',
                'team_id': self.team.id,
                'partner_id': self.partner.id,
                'opportunity_id': self.opportunity.id,
                'sentiment': 'very_negative',
                'summary': 'Customer may cancel after downtime and unresolved issue.',
            }
        )

        self.team.action_run_agent_team()

        signal = self.env['crm.ai.relationship.signal'].search([('summary_id', '=', summary.id)], limit=1)
        self.assertTrue(signal)
        self.assertEqual(signal.signal_type, 'churn_risk')
        self.assertEqual(signal.priority, 'high')

    def test_transcript_processing_creates_summary_and_themes(self):
        transcript = self.env['crm.ai.meeting.transcript'].create(
            {
                'name': 'Zoom Transcript',
                'provider': 'zoom',
                'external_ref': 'zoom-123',
                'team_id': self.team.id,
                'partner_id': self.partner.id,
                'opportunity_id': self.opportunity.id,
                'raw_transcript': (
                    'Customer is happy and excited. '
                    'Discussed renewal terms and enterprise plan upgrade before expiration.'
                ),
            }
        )

        transcript.action_process_transcript()

        self.assertEqual(transcript.ingest_status, 'processed')
        self.assertTrue(transcript.summary_id)
        self.assertIn(transcript.summary_id.sentiment, {'positive', 'very_positive', 'neutral'})
        theme_codes = set(transcript.summary_id.theme_ids.mapped('code'))
        self.assertIn('renewal', theme_codes)
        self.assertIn('upsell', theme_codes)

    def test_create_dummy_dataset_method(self):
        stats = self.env['crm.ai.agent.team'].create_dummy_dataset(
            team_name='Generated Team',
            agent_count=4,
            transcript_count=6,
            auto_run=True,
        )

        team = self.env['crm.ai.agent.team'].browse(stats['team_id'])
        self.assertTrue(team.exists())
        self.assertEqual(stats['agent_count'], 4)
        self.assertEqual(stats['transcript_count'], 6)
        self.assertGreaterEqual(stats['summary_count'], 6)
        self.assertGreaterEqual(stats['run_count'], 1)

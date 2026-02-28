{
    'name': 'AI Lead Nurture Agent',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Automated AI scoring and email generation for leads',
    'description': """
        This module integrates an AI agent into the CRM.
        It automatically evaluates new leads, assigns a score,
        and drafts personalized outreach emails.
    """,
    'depends': ['crm'],
    'data': [
        'views/crm_lead_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

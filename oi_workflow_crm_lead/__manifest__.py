# -*- coding: utf-8 -*-
{
    'name': 'HiTech AFAFERP CRM Lead Workflow Approval',
    'summary': 'CRM Lead Workflow Approval, CRM, Workflow, Approval, Stages, Customer '
               'Relationship Management, Sales, Sales Funnel, Leads',
    'version': '18.0.0.0.7',
    'category': 'Sales/CRM/Workflow',
    'description': '''
        CRM Lead Workflow Approval
         
    ''',
    'author': 'HiTechnologia',
    'license': 'OPL-1',
    'installable': True,
    'depends': ['crm', 'oi_workflow', 'oi_web_selection_field_dynamic'],
    'data': ['data/approval_config.xml',
             'data/mail_template.xml',
             'data/approval_automation.xml',
             'views/crm_lead_views.xml',
             'views/crm_stage_views.xml',
             'data/approval_buttons.xml'],
    'application': False,
    'post_init_hook': 'post_init_hook'
}

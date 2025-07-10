# -*- coding: utf-8 -*-
{
'name': 'HiTech AFAFERP Workflow Engine Base',
'summary': 'Configurable Workflow Engine, Workflow, Workflow Engine, Approval, Approval '
           'Engine, Approval Process, Escalation, Multi Level Approval, Automation, '
           'Workflow Automation',
'version': '18.0.1.8.0',
'category': 'Hidden/Extra Tools',
'description': '''
'''
               '''
'''
               'Odoo standard documents have static status (Purchase Order, Sale Order, '
               '''...)
'''
               'this module allows the  administrator to define a basic workflow (statuses) '
               '''for the model from the odoo interface without the need for a custom module
'''
               '''  - define approval statuses
'''
               '''    (Approval 1, Approval 2, ...)
'''
               '  - define a required condition for each approval status to handle the '
               '''business process 
'''
               '''    (record.amount_total > 1000)
'''
               '''  - set groups for each status
'''
               '''  - automatic notification for approval users
'''
               '  - allow the writing script (python code) to be executed in the approval '
               '''process 
'''
               '''  - define escalation
'''
               '''  - view approval info for each record  
'''
               '''
'''
               '''this module is a base workflow engine
'''
               '''you need a plugin to apply it to standard odoo documents
'''
               '''  - oi_workflow_expense 
'''
               '''  - oi_workflow_hr_contract
'''
               '''  - oi_workflow_hr_holidays
'''
               '''  - oi_workflow_hr_holidays_manager
'''
               '''  - oi_workflow_hr_payslip_run
'''
               '''  - oi_workflow_purchase_order
'''
               '''
'''
               '''To apply it to a manual module, see module oi_workflow_doc
'''
               '''
'''
               '''This module allows to define basic workflow (one way only)
'''
               '''   		 
'''
               '        ',
'author': 'HiTechnologia',
'license': 'OPL-1',
'installable': True,
'depends': ['mail',
             'oi_base',
             'oi_base_cache',
             'web',
             'base_automation',
             'oi_web_selection_field_dynamic',
             'oi_web_selection_tags'],
'data': ['security/ir.model.access.csv',
          'data/ir_sequence.xml',
          'data/approval_record_templates.xml',
          'view/approval_config.xml',
          'view/approval_escalation.xml',
          'view/approval_state_update.xml',
          'view/approval_settings.xml',
          'view/cancellation_record_view.xml',
          'view/action.xml',
          'view/menu.xml',
          'view/templates.xml',
          'data/mail_activity_type.xml',
          'view/res_config_settings.xml',
          'data/ir_cron.xml',
          'data/approval_settings.xml',
          'view/approval_automation.xml',
          'view/approval_buttons.xml',
          'view/approval_process_wizard.xml',
          'view/approval_log.xml',
          'view/ir_model.xml',
          'view/model_expression_editor.xml'],
'assets': {'web.assets_backend': ['oi_workflow/static/src/js/*.js',
                                   'oi_workflow/static/src/xml/*.xml',
                                   'oi_workflow/static/src/scss/*.scss']},
'external_dependencies': {'python': ['humanize']},
'application': False,
'auto_install': True
}
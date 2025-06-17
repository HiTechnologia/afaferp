# -*- coding: utf-8 -*-
{
    'name': 'HiTech AFAFERP Budget Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': """ Budget Management""",
    'description': """ This module allows accountants to manage analytic and 
    budgets.""",
    'author': 'HiTechnologia',
    'company': 'HiTechnologia',
    'maintainer': 'HiTechnologia',
    'depends': ['base', 'account'],
    'data': [
        'security/account_budget_security.xml',
        'security/ir.model.access.csv',
        'views/account_analytic_account_views.xml',
        'views/account_budget_views.xml',
    ],
    'post_init_hook': 'enable_analytic_accounting',
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

# -*- coding: utf-8 -*-
{
    'name': "HiTech AFAFERP Excel Reports",
    "version": "18.0.1.0.0",
    "category": "Sale,Accounting,Warehouse",
    "summary": """For printing excel reports of multiple records""",
    "description": "Print the excel report of the sale,invoice,picking"
                   " of multiple records",
    'author': 'HiTechnologia',
    'company': 'HiTechnologia',
    'maintainer': 'HiTechnolia',
    'depends': ['sale_management', 'account', 'stock'],
    'data': [
        'data/ir_action_data.xml'
    ],
    'assets':
        {
            'web.assets_backend': [
             'hitech_afaferp_advanced_excel_reports\static\src\js\excel_report.js'
            ],
        },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

{
    'name': 'HT AFAF CRM',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Adds custom fields to CRM leads',
    'description': 'This module adds custom fields like WEEK REF#, SELECTED BY MNGT, DATE RECEIVED, etc. to CRM leads.',
    'author': 'HiTech Afaf',
    'depends': ['crm', 'hitech_afaf_project', 'project', 'sale_crm'],
    'data': [
        "views/hitech_afaf_crm.xml",
        "views/hitech_afaf_crm_hide_quick_create.xml",
        "security/ir.model.access.csv"
    ],
    'installable': True,
    'application': False,
}

{
    'name': 'HiTech AFAFERP CRM',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Adds custom fields to CRM leads',
    'description': 'This module adds custom fields like WEEK REF#, SELECTED BY MNGT, DATE RECEIVED, etc. to CRM leads.',
    'author': 'HiTech Afaf',
    'depends': ['crm', 'project', 'sale_crm', 'sale_management', 'hitech_afaf_project'],
    'data': [
        "security/ir.model.access.csv",
        "views/hitech_afaf_crm.xml",
        "views/hitech_afaf_crm_hide_quick_create.xml",
        "views/hitech_afaf_rename_pipeline.xml"
    ],
    'installable': True,
    'application': False,
}

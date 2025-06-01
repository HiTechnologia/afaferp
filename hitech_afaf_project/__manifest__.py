{
    'name': 'HT AFAF Project',
    'version': '1.0',
    'category': 'Project',
    'summary': 'Customizations for project management',
    'description': 'This model adds custom fields to project',
    'author': 'HiTech Afaf',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'views/hitech_afaf_project_view.xml',

    ],
    'installable': True,
    'application': False,
}
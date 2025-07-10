# -*- coding: utf-8 -*-
{
'name': 'HiTech AFAFERP Cache Mixin',
'summary': 'Implementation of cache mixin',
'version': '18.0.1.1.1',
'category': 'Hidden/Extra Tools',
'description': '''
'''
               'implementation of cache.mixin model that allow to read record from memory '
               '''cache instead from query database
'''
               '''used for frequent access master data model
'''
               '''
'''
               '''class MyModel(models.Model):
'''
               '''    _name = 'my.model'
'''
               '''    _inherit = ['cache.mixin']
'''
               '''
'''
               '''records = env['my.model'].search_cached(domain)
'''
               '''		 
'''
               '    ',
'images': [],
'author': 'HiTechnologia',
'license': 'OPL-1',
'installable': True,
'depends': ['base'],
'data': [],
'assets': {},
'external_dependencies': {'python': []},
'auto_install': True,
'application': False
}
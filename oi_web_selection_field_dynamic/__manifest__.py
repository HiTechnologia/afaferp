# -*- coding: utf-8 -*-
{
'name': 'HiTech AFAFERP Dynamic Selection Field Widget',
'summary': 'Dynamic Selection Field Widget',
'version': '18.0.1.1.4',
'category': 'Hidden/Extra Tools',
'description': '''
'''
               '''new widget `selection_dynamic`
'''
               '''add selection options to char field from another selection field
'''
               '''
'''
               '''usage:
'''
               '<field name="purchase_state_char" widget="selection_dynamic" '
               '''selection_model="purchase.order" selection_field="state" />
'''
               '''
'''
               '        ',
'images': [],
'author': 'HiTechnologia',
'license': 'OPL-1',
'installable': True,
'depends': ['web'],
'data': [],
'assets': {'web.assets_backend': ['oi_web_selection_field_dynamic/static/src/js/selection_dynamic_field.js']},
'application': False,
'auto_install': True
}
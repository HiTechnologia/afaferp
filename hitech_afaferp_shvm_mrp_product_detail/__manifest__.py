{
    'name': "HiTech AFAFERP MRP Product Details",
    'version': '18.0.1.0',
    'summary': """It shows the manufacturing detail of product in product view.""",
    'description': '''It shows the manufacturing detail of product in product view.''',
    'author': "HiTechnologia",
    'category': "Manufacturing",
    'depends': ['base', 'mrp'],
    'license': 'LGPL-3',
    'data': [
        'views/product_product_form_view.xml',
        'views/product_template_form_view.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}

{
    'name': 'HiTech AFAFERP Sale Usability',
    'version': '18.0',
    'category': 'Sales',
    'license': 'AGPL-3',
    'summary': 'Usability improvements on sale module',
    'author': 'HiTechnologia',
    'depends': [
        'sale',
        'hitech_afaferp_base_view_inheritance_extension',
        ],
    'data': [
        'views/sale_order.xml',
        'views/sale_report.xml',
        'views/product_pricelist_item.xml',
        'views/account_move.xml',
        'views/res_company.xml',
        ],
    'installable': True,
}

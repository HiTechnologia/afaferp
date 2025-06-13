{
    'name': 'HiTech AFAFERP Account Usability',
    'version': '18.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Small usability enhancements in account module',
    'author': 'HiTechnologia',
    'depends': [
        'account',
        'base_usability',  # needed only to access base_usability.group_nobody
        ],
    'data': [
        'views/account_account.xml',
        'views/account_group.xml',
#        'views/account_bank_statement.xml',
        'views/account_invoice_report.xml',
        'views/account_journal.xml',
        'views/account_move.xml',
        'views/account_move_line.xml',
        'views/account_payment.xml',
        'views/account_analytic_line.xml',
        'views/account_menu.xml',
        'views/account_tax.xml',
#        'views/product.xml',  # TODO
        'views/res_company.xml',
#        'views/account_report.xml',
        'wizards/account_invoice_mark_sent_view.xml',
#        'wizards/account_group_generate_view.xml',
        'wizards/account_move_reversal.xml',
        'security/ir.model.access.csv',
#        'report/invoice_report.xml',  # TODO
        "views/res_partner.xml",
    ],
#    'qweb': ['static/src/xml/account_payment.xml'],
    'installable': True,
#    "post_init_hook": "post_init_hook",
}

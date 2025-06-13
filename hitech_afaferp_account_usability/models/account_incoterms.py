from odoo import models


class AccountIncoterms(models.Model):
    _inherit = 'account.incoterms'
    _rec_names_search = ["name", "code"]

    _sql_constraints = [(
        'code_unique',
        'unique(code)',
        'This incoterm code already exists.')]

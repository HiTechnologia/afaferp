from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_warn = fields.Selection(tracking=True)

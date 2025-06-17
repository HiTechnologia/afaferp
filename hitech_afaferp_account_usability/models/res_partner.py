from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_warn = fields.Selection(tracking=True)
    property_account_position_id = fields.Many2one(tracking=True)

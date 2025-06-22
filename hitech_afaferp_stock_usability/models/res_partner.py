from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    picking_warn = fields.Selection(tracking=True)

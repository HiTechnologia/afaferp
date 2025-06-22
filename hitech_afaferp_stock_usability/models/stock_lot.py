from odoo import fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    name = fields.Char(tracking=True)
    ref = fields.Char(tracking=True)
    product_id = fields.Many2one(tracking=True)
    company_id = fields.Many2one(tracking=True)

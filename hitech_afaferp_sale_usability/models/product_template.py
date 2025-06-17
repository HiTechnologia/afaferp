from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_type = fields.Selection(tracking=True)
    expense_policy = fields.Selection(tracking=True)
    sale_line_warn = fields.Selection(tracking=True)

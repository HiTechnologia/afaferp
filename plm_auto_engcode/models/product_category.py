from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = "product.category"

    plm_code_sequence = fields.Many2one("ir.sequence", string="Part Number sequence")

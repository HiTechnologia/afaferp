from odoo import models, fields, api, _


class ProductVariants(models.Model):
    _inherit = 'product.product'

    production_ids = fields.One2many('mrp.production', 'product_id')

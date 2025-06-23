from odoo import models
from odoo import fields
from odoo import _


class ProductCategory(models.Model):
    _inherit = ['product.category']

    kit_bom = fields.Boolean(_('KIT Bom Type'))


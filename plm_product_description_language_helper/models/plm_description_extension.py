from odoo import fields, models


class PlmDescriptionExtension(models.Model):
    _inherit = "plm.description"

    description = fields.Char(translate=True)

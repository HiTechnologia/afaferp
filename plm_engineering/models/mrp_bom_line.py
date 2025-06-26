from odoo import fields, models


class MrpBomLineExtension(models.Model):
    _inherit = 'mrp.bom.line'

    ebom_source_id = fields.Integer('Source E-Bom ID')

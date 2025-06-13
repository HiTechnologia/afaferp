from odoo import api, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    @api.depends('name', 'model')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.name} ({rec.model})'

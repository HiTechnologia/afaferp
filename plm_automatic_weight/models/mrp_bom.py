
from odoo import models


class MrpBomExtension(models.Model):
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'

    def force_compute_bom_weight(self):
        """
            Call plm bom weight calculator function
        """
        self.rebase_bom_weight()

    def get_bom_child_weight(self):
        self.ensure_one()
        out = 0.0
        for mrp_bom_id in self:
            for bom_line_id in mrp_bom_id.bom_line_ids:
                out+= bom_line_id.product_id.weight  * bom_line_id.product_qty
        return out



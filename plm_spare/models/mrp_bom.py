from odoo import fields, models


class MrpBomExtension(models.Model):
    _inherit = "mrp.bom"

    type = fields.Selection(
        selection_add=[("spbom", "Spare BoM")], ondelete={"spbom": "cascade"}
    )


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    is_spare_part = fields.Boolean(related="product_id.is_spare_part")

    def action_mrp_product_spare(self):
        pass

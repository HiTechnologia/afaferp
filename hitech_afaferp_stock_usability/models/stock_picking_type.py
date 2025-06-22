from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_dropship = fields.Boolean(compute="_compute_is_dropship", store=True)

    @api.depends("code", "warehouse_id", "default_location_src_id", "default_location_dest_id")
    def _compute_is_dropship(self):
        supplier_loc_id = self.env.ref("stock.stock_location_suppliers").id
        customer_loc_id = self.env.ref("stock.stock_location_customers").id
        for picktype in self:
            is_dropship = False
            if (
                    picktype.code == 'incoming'
                    and not picktype.warehouse_id
                    and picktype.default_location_src_id.id == supplier_loc_id
                    and picktype.default_location_dest_id.id == customer_loc_id
                    ):
                is_dropship = True
            picktype.is_dropship = is_dropship

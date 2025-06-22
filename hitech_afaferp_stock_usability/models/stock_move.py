from odoo import fields, models, _
import logging

logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    # for optional display in tree view
    product_barcode = fields.Char(
        related='product_id.barcode', string="Product Barcode")

    def button_do_unreserve(self):
        for move in self:
            move._do_unreserve()
            picking = move.picking_id
            if picking:
                product = move.product_id
                picking.message_post(body=_(
                    "Product <a href=# data-oe-model=product.product "
                    "data-oe-id=%d>%s</a> qty %s %s <b>unreserved</b>")
                    % (product.id, product.display_name,
                       move.product_qty, product.uom_id.name))
                # fields 'product_qty' has digits=0... strange. So I can't use formatLang()
                # Copied from do_unreserved of stock.picking
                picking.package_level_ids.filtered(lambda p: not p.move_ids).unlink()

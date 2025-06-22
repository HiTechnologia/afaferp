from odoo import fields, models, _
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError
from markupsafe import Markup
import logging

logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # for optional display in list view
    product_barcode = fields.Char(
        related='product_id.barcode', string="Product Barcode")

    # TODO: I think it's not complete
    def button_do_unreserve(self):
        for moveline in self:
            if moveline.state == 'cancel':
                continue
            elif moveline.state == 'done':
                raise UserError(_(
                    "You cannot unreserve a move line in done state."))
            picking = moveline.move_id.picking_id
            if picking:
                product = moveline.product_id
                product_link = Markup(
                    "<a href=# data-oe-model=product.product data-oe-id=%s>%s</a>" % (product.id, product.display_name))
                picking.message_post(body=_(
                    "Product %(product_link)s qty %(qty)s %(uom)s unreserved",
                    product_link=product_link,
                    qty=formatLang(self.env, moveline.quantity, dp='Product Unit of Measure'),
                    uom=product.uom_id.name))
                # Copied from do_unreserved of stock.picking
                picking.package_level_ids.filtered(lambda p: not p.move_ids).unlink()
            moveline.unlink()

from odoo import fields, models
import logging

logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    # In the 'stock' module, the default value for 'trigger' is 'auto'
    # but all the Odoo deployments I've seen so far need 'manual' by default
    trigger = fields.Selection(default='manual')
    product_barcode = fields.Char(related='product_id.barcode', string="Product Barcode")
    seller_id = fields.Many2one(
        "res.partner",
        compute="_compute_seller_id",
        search="_search_seller_id",
        string="Main Supplier")

    def _search_seller_id(self, operator, value):
        # searching on the first line of a o2m is not that easy
        # So we search all potential matching products
        # Then we filter on the seller_id
        records = self.search([("product_id.seller_ids.partner_id", operator, value)])
        records = records.filtered_domain([("seller_id", operator, value)])
        return [("id", "in", records.ids)]

    def _compute_seller_id(self):
        for orderpoint in self:
            orderpoint.seller_id = fields.first(orderpoint.product_id.seller_ids).partner_id

    def _procure_orderpoint_confirm(
            self, use_new_cursor=False, company_id=None, raise_user_error=True):
        logger.info(
            'procurement scheduler: START to create moves from '
            'orderpoints')
        res = super()._procure_orderpoint_confirm(
            use_new_cursor=use_new_cursor, company_id=company_id,
            raise_user_error=raise_user_error)
        logger.info(
            'procurement scheduler: END creation of moves from '
            'orderpoints')
        return res

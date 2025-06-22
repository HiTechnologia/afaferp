from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    # In the stock module: _order = "is_favorite desc, sequence, id"

    partner_id = fields.Many2one(tracking=True)
    picking_type_id = fields.Many2one(tracking=True)
    move_type = fields.Selection(tracking=True)
    is_locked = fields.Boolean(tracking=True)

    def do_unreserve(self):
        res = super().do_unreserve()
        for pick in self:
            pick.message_post(body=_("Picking <b>unreserved</b>."))
        return res

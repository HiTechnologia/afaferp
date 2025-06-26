from odoo import api, fields, models


class PlmBreakages(models.Model):
    _name = "plm.breakages"
    _description = "PLM Breakages"
    _inherit = "mail.thread"

    name = fields.Char(readonly=True, required=True, copy=False, default="New")
    product_id = fields.Many2one("product.product", "Product")
    parent_id = fields.Many2one("product.product", "Parent")
    partner_id = fields.Many2one("res.partner", "Customer")
    lot_number = fields.Char("Lot/Serial Number")
    date = fields.Date("Date", required=True, copy=False, default=fields.Date.today)
    notes = fields.Text("Notes")
    tracking = fields.Selection(related="product_id.tracking")

    @api.model_create_multi
    def create(self, vals):
        for vals_dict in vals:
            if vals_dict.get("name", "New") == "New":
                seq_date = None
                if "date_order" in vals:
                    seq_date = fields.Datetime.context_timestamp(
                        self, fields.Datetime.to_datetime(vals_dict["date_order"])
                    )
                vals_dict["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "plm.breakages", sequence_date=seq_date
                    )
                    or "/"
                )
        return super().create(vals)

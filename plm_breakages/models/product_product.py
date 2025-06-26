from odoo import _, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    breakages_count = fields.Integer(
        "# Breakages", compute="_compute_breakages_count", compute_sudo=False
    )

    def open_breakages(self):
        return {
            "name": _("Products"),
            "res_model": "plm.breakages",
            "view_type": "form",
            "view_mode": "list,form",
            "type": "ir.actions.act_window",
            "domain": [("product_id", "=", self.id)],
            "context": {"default_product_id": self.id},
        }

    def _compute_breakages_count(self):
        for product in self:
            product.breakages_count = self.env["plm.breakages"].search_count(
                [("product_id", "=", product.id)]
            )

from odoo import _, fields, models


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    breakages_count = fields.Integer(
        "# Breakages", compute="_compute_breakages_count", compute_sudo=False
    )

    def open_breakages(self):
        product_id = self.product_id

        return {
            "name": _("Products"),
            "res_model": "plm.breakages",
            "view_type": "form",
            "view_mode": "list,form,pivot",
            "type": "ir.actions.act_window",
            "domain": [("product_id", "=", product_id.id)],
            "context": {"default_parent_id": product_id.id},
        }

    def _compute_breakages_count(self):
        for mrp_bom_line in self:
            product_id = mrp_bom_line.product_id
            mrp_bom_line.breakages_count = self.env["plm.breakages"].search_count(
                [("product_id", "=", product_id.id)]
            )

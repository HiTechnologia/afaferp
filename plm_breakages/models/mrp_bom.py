from odoo import _, fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    breakages_count = fields.Integer(
        "# Breakages", compute="_compute_breakages_count", compute_sudo=False
    )

    def open_breakages(self):
        product_id = self.product_id
        product_ids = self.get_bom_product_breakeges()
        return {
            "name": _("Products"),
            "res_model": "plm.breakages",
            "view_type": "form",
            "view_mode": "list,form,pivot",
            "type": "ir.actions.act_window",
            "domain": [("product_id", "in", product_ids)],
            "context": {"default_parent_id": product_id.id},
        }

    def get_bom_product_breakeges(self):
        out = []
        for mrp_bom in self:
            product_id = mrp_bom.product_id
            out.append(product_id.id)
            out.extend(mrp_bom.bom_line_ids.mapped("product_id").ids)
        return out

    def _compute_breakages_count(self):
        for mrp_bom in self:
            product_ids = self.get_bom_product_breakeges()
            mrp_bom.breakages_count = self.env["plm.breakages"].search_count(
                [("product_id", "in", product_ids)]
            )

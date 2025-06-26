from odoo import api, models
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUSES


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        conditional_status = RELEASED_STATUSES.copy()
        config_param = self.env["ir.config_parameter"].sudo()
        conditional_status.extend(
            config_param.get_param("purchase_only_latest_params", "").split(",")
        )
        if self.env.context.get("purchase_latest"):
            args += [
                "|",
                ("engineering_code", "=", False),
                ("engineering_state", "in", conditional_status),
            ]

        return super(ProductProduct, self).name_search(
            name=name, args=args, operator=operator, limit=limit
        )

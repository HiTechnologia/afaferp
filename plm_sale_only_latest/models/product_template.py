from odoo import api, models
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUSES


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        conditional_status = RELEASED_STATUSES.copy()
        config_param = self.env["ir.config_parameter"].sudo()
        conditional_status.extend(
            config_param.get_param("sales_only_latest_params", "").split(",")
        )
        if self.env.context.get("sale_latest"):
            args += [
                "|",
                ("engineering_code", "=", False),
                ("engineering_state", "in", conditional_status),
            ]

        return super(ProductTemplate, self).name_search(
            name=name, args=args, operator=operator, limit=limit
        )

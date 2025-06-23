from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @property
    def actions(self):
        action_dict = super(ProductProduct, self).actions
        action_dict["suspended"] = self.action_suspend
        return action_dict

    def action_suspend(self):
        """
        reactivate the object
        """
        defaults = {
            "old_state": self.engineering_state,
            "engineering_state": "suspended",
        }
        obj_id = self.write(defaults)
        self.product_tmpl_id.write(defaults)
        return obj_id

    def action_unsuspend(self):
        """
        reactivate the object
        """
        defaults = {
            "old_state": self.engineering_state,
            "engineering_state": self.old_state,
        }
        obj_id = self.write(defaults)
        self.product_tmpl_id.write(defaults)
        return obj_id

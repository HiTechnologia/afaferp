from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def before_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx["active_id"] = self.product_variant_id.id
        ctx["active_model"] = "product.product"
        ctx["wf_action"] = "before"
        for action in self.env["plm.automatedwfaction"].search(
            [
                ("apply_to", "=", "product.product"),
                ("from_state", "=", from_state),
                ("to_state", "=", to_state),
                ("before_after", "=", "before"),
            ]
        ):
            action.with_context(ctx)._run()

    def after_move_to_state(self, from_state, to_state):
        """
        technical function for workflow customization
        :from_state state that came from
        :to_state state to go
        """
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx["active_id"] = self.product_variant_id.id
        ctx["active_model"] = "product.product"
        ctx["wf_action"] = "after"
        for action in self.env["plm.automatedwfaction"].search(
            [
                ("apply_to", "=", "product.product"),
                ("from_state", "=", from_state),
                ("to_state", "=", to_state),
                ("before_after", "=", "after"),
            ]
        ):
            action.with_context(ctx)._run()

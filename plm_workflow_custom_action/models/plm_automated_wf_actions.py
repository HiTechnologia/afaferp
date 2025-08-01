import json

from odoo import fields, models
from odoo.addons.plm.models.plm_mixin import USED_STATES


class PlmAutomatedWFAction(models.Model):
    _name = "plm.automatedwfaction"
    _description = "Plm Automated Work Flow Actions"

    name = fields.Char("Action Name")
    from_state = fields.Selection(USED_STATES, string="From Stare")
    to_state = fields.Selection(USED_STATES, string="To State")
    before_after = fields.Selection([
        ("before", "Before"),
        ("after", "After")], string="Perform",
        help="you can choose to perform the action before or after the workflow action"
    )

    apply_to = fields.Selection(
        [("product.product", "Product"), ("ir.attachment", "Attachment")],
        string="Apply To",
        help="Apply this action to the workflow model",
    )

    domain = fields.Char("Domain", help="""specifie the domain of the action""")

    child_ids = fields.Many2many(
        "ir.actions.server",
        "rel_plm_server_actions",
        "server_id",
        "action_id",
        string="Child Actions",
        help="Child server actions that will be executed."
             "Note that the last return returned action value"
             " will be used as global return value.",
    )

    def name_get(self):
        out = []
        for o in self:
            out.append(
                (o.id, "[%s | %s] %s" % (o.to_state, o.before_after, o.name or ""))
            )
        return out

    def _run(self):
        res = False
        active_id = self.env.context["active_id"]
        active_model = self.env.context["active_model"]
        if active_model == self.apply_to:
            base_domain = [("id", "=", active_id)]
            for act in self.child_ids.sorted():
                if self.domain:
                    base_domain = base_domain + json.loads(self.domain.replace("'", ""))
                    obj_id = self.env[active_model].search(base_domain)
                else:
                    obj_id = self.env[active_model].browse(active_id)
                if obj_id:
                    res = act.run() or res
        return res

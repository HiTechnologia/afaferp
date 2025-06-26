from odoo import _, fields, models
from datetime import datetime


class ProductExtension(models.Model):
    _inherit = "product.product"

    project_ids = fields.Many2many(
        "project.project",
        "project_product_rel",
        "product_id",
        "project_id",
        string=_("Projects"),
    )
    activity_task_id = fields.Many2one("project.task", _("Activity Task"))

    def createConfirmActivity(self):
        for comp_obj in self:
            ref_user = self.env["res.users"]
            if comp_obj.activity_task_id:
                ref_user = comp_obj.activity_task_id.project_id.user_id
            if not ref_user and comp_obj.project_ids:
                for project in comp_obj.project_ids:
                    ref_user += project.user_id
            ref_user.union()
            if ref_user:
                mail_activity = self.env["mail.activity"]
                mail_activity.create(
                    {
                        "res_model_id": self.env["ir.model"]
                        .search([("model", "=", self._name)])
                        .id,
                        "res_id": comp_obj.id,
                        "recommended_activity_type_id": False,
                        "activity_type_id": self.env.ref(
                            "plm_project.mail_activity_product_confirmed"
                        ).id,
                        "summary": "Product %r confirmed" % (comp_obj.display_name),
                        "date_deadline": str(datetime.now().date()),
                        "user_id": ref_user.id,
                        "note": "<div>Confirmed product: %s</div>"
                        % (comp_obj.display_name),
                    }
                )

    def action_confirm(self):
        for comp_obj in self:
            if not self.env.context.get("activity_created", False):
                comp_obj.createConfirmActivity()
            super(
                ProductExtension, comp_obj.with_context(activity_created=True)
            ).action_confirm()
        return True

    def action_release(self):
        for product in self:
            self.env["mail.activity"].search(
                [
                    (
                        "activity_type_id",
                        "=",
                        self.env.ref("plm_project.mail_activity_product_confirmed").id,
                    ),
                    ("res_id", "=", product.id),
                    (
                        "res_model_id",
                        "=",
                        self.env["ir.model"]
                        .sudo()
                        .search([("model", "=", self._name)])
                        .id,
                    ),
                ]
            ).action_done()
        return super().action_release()

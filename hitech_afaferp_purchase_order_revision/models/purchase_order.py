from odoo import fields, models, api
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = ["purchase.order", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Current Revision",
        index=True,
        ondelete="set null",
    )
    old_revision_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="current_revision_id",
        string="Old Revisions",
    )

    # These two fields must exist for your revision system to work:
    unrevisioned_name = fields.Char(string="Unrevisioned Name", required=True, index=True)
    revision_number = fields.Integer(string="Revision Number", default=0)

    has_old_revisions = fields.Boolean(
        compute="_compute_revision_stats",
        store=True,
        string="Has Old Revisions"
    )
    revision_count = fields.Integer(
        compute="_compute_revision_stats",
        store=True,
        string="Revision Count"
    )

    @api.depends("old_revision_ids")
    def _compute_revision_stats(self):
        for order in self:
            order.revision_count = len(order.old_revision_ids)
            order.has_old_revisions = bool(order.old_revision_ids)

    @api.constrains("unrevisioned_name", "revision_number", "company_id")
    def _check_revision_unique(self):
        for record in self:
            domain = [
                ("unrevisioned_name", "=", record.unrevisioned_name),
                ("revision_number", "=", record.revision_number),
                ("company_id", "=", record.company_id.id),
                ("id", "!=", record.id),
            ]
            if self.env["purchase.order"].search(domain, limit=1):
                raise ValidationError(
                    "Order Reference and revision must be unique per Company."
                )

    def _prepare_revision_data(self, new_revision):
        vals = super()._prepare_revision_data(new_revision)
        vals["state"] = "cancel"
        return vals

    def create_revision(self):
        self.ensure_one()
        # Simple example: clone current order with incremented revision_number
        revision = self.copy({
            "revision_number": self.revision_number + 1,
            "current_revision_id": self.id,
            "state": "draft",
        })
        self.old_revision_ids = [(4, revision.id)]
        return revision

    def action_view_revisions(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        action["domain"] = ["|", ("active", "=", False), ("active", "=", True)]
        action["context"] = {
            "active_test": False,
            "search_default_current_revision_id": self.id,
            "default_current_revision_id": self.id,
        }
        return action

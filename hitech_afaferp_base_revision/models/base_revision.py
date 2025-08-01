from odoo import _, api, fields, models


class BaseRevision(models.AbstractModel):
    _name = "base.revision"
    _description = "Document Revision (abstract)"

    @api.depends("old_revision_ids")
    def _compute_has_old_revisions(self):
        for rec in self:
            rec.has_old_revisions = (
                True if rec.with_context(active_test=False).old_revision_ids else False
            )

    current_revision_id = fields.Many2one(
        comodel_name="base.revision",
        string="Current revision",
        readonly=True,
        copy=True,
    )
    old_revision_ids = fields.One2many(
        comodel_name="base.revision",
        inverse_name="current_revision_id",
        string="Old revisions",
        readonly=True,
        domain=["|", ("active", "=", False), ("active", "=", True)],
        context={"active_test": False},
    )
    revision_number = fields.Integer(string="Revision", copy=False, default=0)
    unrevisioned_name = fields.Char(
        string="Original Reference", copy=True, readonly=True
    )
    active = fields.Boolean(default=True)
    has_old_revisions = fields.Boolean(compute="_compute_has_old_revisions")
    revision_count = fields.Integer(
        compute="_compute_revision_count", string="Previous versions count"
    )

    @api.depends("old_revision_ids")
    def _compute_revision_count(self):
        res = self.with_context(active_test=False).read_group(
            domain=[("current_revision_id", "in", self.ids)],
            fields=["current_revision_id"],
            groupby=["current_revision_id"],
        )
        revision_dict = {
            x["current_revision_id"][0]: x["current_revision_id_count"] for x in res
        }
        for rec in self:
            rec.revision_count = revision_dict.get(rec.id, 0)

    _sql_constraints = [
        (
            "revision_unique",
            "unique(unrevisioned_name, revision_number)",
            "Reference and revision must be unique.",
        )
    ]

    def copy(self, default=None):
        default = default or {}
        if "unrevisioned_name" not in default:
            default["unrevisioned_name"] = False
        revision_records = super().copy(default=default)
        for rec in revision_records:
            if rec.unrevisioned_name:
                continue
            name_field = self._context.get("revision_name_field", "name")
            rec.write({"unrevisioned_name": rec[name_field]})
        return revision_records

    def _get_new_rev_data(self, new_rev_number):
        self.ensure_one()
        return {
            "revision_number": new_rev_number,
            "unrevisioned_name": self.unrevisioned_name,
            "name": "%s-%02d" % (self.unrevisioned_name, new_rev_number),
            "old_revision_ids": [(4, self.id, False)],
        }

    def _prepare_revision_data(self, new_revision):
        return {"active": False, "current_revision_id": new_revision.id}

    def copy_revision_with_context(self):
        default_data = self.default_get([])
        new_rev_number = self.revision_number + 1
        vals = self._get_new_rev_data(new_rev_number)
        default_data.update(vals)
        new_revision = self.copy(default_data)
        self.old_revision_ids.write({"current_revision_id": new_revision.id})
        self.write(self._prepare_revision_data(new_revision))
        return new_revision

    @api.model_create_multi
    def create(self, vals_list):
        name_field = self._context.get("revision_name_field", "name")
        for vals in vals_list:
            if "unrevisioned_name" not in vals:
                vals["unrevisioned_name"] = vals[name_field]

        return super().create(vals_list)

    def create_revision(self):
        revision_ids = []
        # Looping over records
        for rec in self:
            # Calling  Copy method
            copied_rec = rec.copy_revision_with_context()
            if hasattr(self, "message_post"):
                msg = _("New revision created: %s") % copied_rec.name
                copied_rec.message_post(body=msg)
                rec.message_post(body=msg)
            revision_ids.append(copied_rec.id)
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "name": _("New Revisions"),
            "res_model": self._name,
            "domain": f"[('id', 'in', {revision_ids})]",
            "target": "current",
        }
        return action

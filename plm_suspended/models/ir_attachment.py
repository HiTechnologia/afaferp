from odoo import _, api, fields, models
from odoo.addons.plm.models.plm_mixin import USED_STATES

USED_STATES.append(("suspended", _("Suspended")))


class PlmDocumentExtension(models.Model):
    _inherit = "ir.attachment"

    engineering_state = fields.Selection(
        USED_STATES,
        string="Status",
        readonly=True,
        default="draft",
        help=_("The status of the product."),
    )
    old_state = fields.Char(name="Old Status")

    @property
    def actions(self):
        action_dict = super(PlmDocumentExtension, self).actions
        action_dict["suspended"] = self.action_suspend
        return action_dict

    def action_suspend(self):
        """
        reactivate the object
        """
        if self.ischecked_in():
            defaults = {
                "old_state": self.engineering_state,
                "engineering_state": "suspended",
            }
            return self.with_context(check=False).write(defaults)
        return False

    def action_unsuspend(self):
        """
        reactivate the object
        """
        if self.ischecked_in():
            defaults = {
                "old_state": self.engineering_state,
                "engineering_state": self.old_state,
            }
            return self.with_context(check=False).write(defaults)
        return False

    @api.model
    def is_plm_state_writable(self):
        if super(PlmDocumentExtension, self).is_plm_state_writable():
            for customObject in self:
                if customObject.engineering_state in ("suspended",):
                    return False
            return True
        else:
            return False

from odoo import _, fields, models


class PlmDocumentExtension(models.Model):
    _inherit = "ir.attachment"

    used_for_spare = fields.Boolean(
        _("Used for Spare"),
        help=_("Drawings marked here will be used printing Spare Part Manual report."),
    )

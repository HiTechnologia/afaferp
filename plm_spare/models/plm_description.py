from odoo import _, fields, models


class PlmDescriptionExtension(models.Model):
    _inherit = "plm.description"

    bom_tmpl = fields.Many2one(
        "mrp.bom",
        _("Choose a BoM"),
        change_default=True,
        help=_("Select a  BoM as template to drive building Spare BoM."),
    )

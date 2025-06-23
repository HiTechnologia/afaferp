from odoo import _, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    engineering_state = fields.Selection(
        selection_add=[("suspended", _("Suspended"))]
    )
    old_state = fields.Char(size=128, name=_("Old Status"))

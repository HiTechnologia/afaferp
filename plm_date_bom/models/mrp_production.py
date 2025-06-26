from odoo import _, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    obsolete_presents = fields.Boolean(
        _("Obsolete presents"), related="bom_id.obsolete_presents"
    )

from odoo import _, fields, models


class ProductTemplateCuttedParts(models.Model):
    _inherit = "product.template"
    row_material = fields.Many2one("product.product", _("Raw Material Product"))
    row_material_factor = fields.Float("Raw Material Conversion Factor")
    row_material_x_length = fields.Float(_("X Raw Material length"), default=1.0)
    row_material_y_length = fields.Float(_("Y Raw Material length"), default=1.0)
    wastage_percent = fields.Float(_("X Percent Wastage"))
    wastage_percent_y = fields.Float(_("Y Percent Wastage"))
    material_added = fields.Float(_("X Material Wastage"))
    material_added_y = fields.Float(_("Y Material Wastage"))
    is_row_material = fields.Boolean(_("Is Raw Material"))

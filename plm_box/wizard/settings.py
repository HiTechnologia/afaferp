from odoo import _, fields, models


class stock_config_settings(models.TransientModel):
    _inherit = "res.config.settings"

    module_stock_plm_box = fields.Boolean(
        _("Allow plm_box relation"), help=_("Adds plm_box relation to Warehouse.")
    )
    module_plm_box_widget = fields.Boolean(
        _("Plm Widget"), help=_("Adds plm_box relation to Warehouse.")
    )

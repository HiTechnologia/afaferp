
from odoo import models

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        if self.env.user._is_internal():
            res['disable_edit_on_non_approval'] = self.env['ir.config_parameter'].sudo().get_param("disable_edit_on_non_approval") == "True"
        return res

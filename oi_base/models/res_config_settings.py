import odoo
from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    is_enterprise = fields.Boolean(compute = "_calc_is_enterprise")
    
    @api.depends('company_id')
    def _calc_is_enterprise(self):
        version_info = odoo.service.common.exp_version()
        self.is_enterprise = version_info['server_version_info'][-1] == "e"
    
    def onchange_module(self, field_value, module_name):
        if int(field_value) and not self.env["ir.module.module"].get_module_info(module_name[7:]):
            self[module_name] = False
            return {
                'warning': {
                    'title': _('Warning!'),
                    'message': _('Module (%s) is not available in your system', module_name[7:]),
                }
            }                        
        return super().onchange_module(field_value, module_name)
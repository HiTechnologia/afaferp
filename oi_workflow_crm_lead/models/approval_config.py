from odoo import models, api

class ApprovalConfig(models.Model):
    _inherit = 'approval.config'
    
    def _need_crm_states_sync(self):
        return self.env.registry.ready and any(r.model == 'crm.lead' for r in self)
        
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        if records._need_crm_states_sync():            
            self.env['crm.stage']._states_sync()
        
        return records
    
    def write(self, vals):
        res = super().write(vals)
        if self._need_crm_states_sync():            
            self.env['crm.stage']._states_sync()        
        return res
    
    def unlink(self):
        crm_states_sync = self._need_crm_states_sync()
        res = super().unlink()
        
        if crm_states_sync:
            self.env['crm.stage']._states_sync()
        
        return res
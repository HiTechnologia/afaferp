
from odoo import models, fields, api

class ApprovalSettingsStatus(models.Model):
    _name = 'approval.settings.state'
    _inherit = ['cache.mixin', 'xml_id.mixin']
    _description = 'Approval Workflow Static Status'
    _order = 'type desc,sequence'

    settings_id = fields.Many2one('approval.settings', required = True, ondelete='cascade', string='Model Settings')
    model_id = fields.Many2one(related='settings_id.model_id', store = True)
    sequence = fields.Integer(default = 0, required = True, copy = False)
    state = fields.Char(required = True, string="Status")
    name = fields.Char(required = True, translate = True)
    active = fields.Boolean(default = True)
    type = fields.Selection([('before', 'Before Approval'), ('after', 'After Approval')], required = True)
    reject_state = fields.Boolean('Reject Status')    
    
    _sql_constraints = [
        ('state_uniq', 'unique (settings_id,state)', 'The state should be unique !'),
    ]    
        
    @api.onchange('sequence')
    def _onchange_sequence(self):
        if self.settings_id and not self.sequence:
            sequences = self.mapped('settings_id.state_ids.sequence')
            self.sequence = (sequences and max(sequences) or 0) + 1
            
            
    @api.model_create_multi
    @api.returns('self', lambda value:value.id)
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records
    
    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res
    
    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res
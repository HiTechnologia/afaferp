
from odoo import models, fields

class ApprovalEscalation(models.Model):
    _name = 'approval.escalation'
    _description = 'Approval Workflow Escalation'
    _order = 'sequence,id'
    
    config_id = fields.Many2one('approval.config', required = True, ondelete ='cascade')    
    automation_id = fields.Many2one('base.automation', string='Automated Action', required=True, ondelete='restrict', delegate=True)
    active = fields.Boolean(related='automation_id.active', store = True, readonly = False)
    sequence = fields.Integer()
            
    def unlink(self):
        automation_ids = self.mapped('automation_id')
        res = super(ApprovalEscalation, self).unlink()
        automation_ids.unlink()
        return res
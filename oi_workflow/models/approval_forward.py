
from odoo import models, fields

class ApprovalForward(models.Model):
    _name = 'approval.forward'
    _description = 'Approval Forward'
    
    model_id = fields.Many2one('ir.model', string='Object', required = True, ondelete='cascade')
    record_id = fields.Integer(required = True)
    approval_state_id = fields.Many2one('approval.config', required = True, ondelete='cascade')
    active = fields.Boolean(default = True)
    user_id = fields.Many2one('res.users', required = True, ondelete='cascade')
    
    forwarder_user_id = fields.Many2one('res.users', required = True, ondelete='cascade')
    
    _sql_constraints = [
        ('duplicate_check', 'EXCLUDE USING btree (model_id WITH =, record_id WITH =, approval_state_id WITH =) WHERE (active)', 'Duplicate Forward Record!'),
    ]      
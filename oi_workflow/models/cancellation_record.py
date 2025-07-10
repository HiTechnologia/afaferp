from odoo import models, fields, api, _
from odoo.tools import index_exists, create_index
from ..api import on_approve

class CancellationRecord(models.Model):
    _name = 'cancellation.record'
    _inherit =['approval.record', 'mail.thread', 'mail.activity.mixin', 'name.sequence.mixin']
    _description = 'Cancellation Record Workflow Log'
    _order = 'id desc'
    
    requester_id = fields.Many2one('res.users', required = True, default = lambda self: self.env.user)
    model_id = fields.Many2one('ir.model', string='Object', required = True, ondelete='cascade')
    model = fields.Char(related='model_id.model', compute_sudo = True)
    record_id = fields.Many2oneReference(required = True, model_field='model')
    reason = fields.Char()    
    
    def _auto_init(self):
        super()._auto_init()
        if not index_exists(self.env.cr, 'cancellation_record_record_idx'):
            create_index(self.env.cr, 'cancellation_record_record_idx', self._table, ["model_id", "record_id"])    
                
    def get_record(self):
        record = self.env[self.model_id.model].browse(self.record_id) or self.env["approval.record"]
        return record and record.exists()
                
    @on_approve()
    def _cancel_target_record(self):
        return self.get_record()._action_cancel()
    
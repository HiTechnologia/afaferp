from odoo import models, fields, api

class MailActivity(models.Model):
    _inherit = 'mail.activity'
    
    hide_in_chatter = fields.Boolean(compute = "_compute_hide_in_chatter")
    
    @api.depends('activity_type_id', 'automated')
    def _compute_hide_in_chatter(self):
        activity_type_approval = self.env.ref('oi_workflow.activity_type_approval')
        for record in self:
            record.hide_in_chatter = record.activity_type_id == activity_type_approval and record.automated
from odoo import models, fields, api, _

class ApprovalLogVoting(models.Model):
    _name = 'approval.log.voting'
    _description = 'Approval Log Voting'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True)
    vote = fields.Selection([('approve', 'Approve'), ('reject', 'Reject')], string='Vote', required=True)
    button_id = fields.Many2one('approval.buttons', string='Approval Button', required=True)
    button_name = fields.Char(related='button_id.name', string='Button Name', readonly=True)
    comment = fields.Html(string='Comment')
    model_id = fields.Many2one('ir.model', string='Object', required = True, ondelete='cascade')
    model = fields.Char(related='model_id.model', string='Model', readonly=True, store=True)
    record_id = fields.Many2oneReference(required = True, model_field="model")
    create_date = fields.Datetime(string='Voted On', readonly=True)
    state = fields.Char(string='Voting State', required=True)
    button_class = fields.Selection(string='Button Class', related='button_id.button_class', readonly=True)
    
    _sql_constraints = [
        ('unique_user_model', 'unique(user_id, model_id, record_id, state)', 'A user can only vote once per model!')
    ]

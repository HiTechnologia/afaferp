from odoo import models, fields, api, _

class Lead(models.Model):
    _name = "crm.lead"
    _inherit = ['approval.record', "crm.lead"]
    _default_field_readonly = "state != 'draft' and not user_can_approve"
    
    stage_id = fields.Many2one(inverse = "_set_stage_id")
    state = fields.Selection(tracking = False)

    @api.model
    def _before_approval_states(self):
        return [('draft', _('New'))]

    @api.model
    def _after_approval_states(self):
        return [('won', _('Won')), ('lost', _('Lost')), ('rejected', _('Rejected'))]

    @api.depends('state')
    def _compute_stage_id(self):
        for lead in self:
            lead.stage_id = self.env['crm.stage'].search([('state', '=', lead.state)], limit=1)
            
    @api.depends('state', 'approval_state_id', 'active')
    def _calc_approval_user_ids(self):
        archived = self.filtered(lambda r: not r.active)
        super(Lead, self - archived)._calc_approval_user_ids()
        if archived:
            archived.approval_user_ids = False
            archived.approval_partner_ids = False
            archived.user_can_approve = False
            archived.approval_done_user_ids = False
            
    @api.depends('state', 'approval_state_id', 'active')
    def _calc_waiting_approval(self):
        archived = self.filtered(lambda r: not r.active)
        super(Lead, self - archived)._calc_waiting_approval()
        archived.waiting_approval = False
            

    def _set_stage_id(self):
        for record in self:
            if record.stage_id.state != record.state:
                record.state = record.stage_id.state
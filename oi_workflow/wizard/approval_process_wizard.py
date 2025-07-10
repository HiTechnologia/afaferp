from odoo import models, fields, api
from ..models.approval_record import ApprovalRecord

class ApprovalProcessWizard(models.TransientModel):
    _name = 'approval.process.wizard'
    _description = 'Approval Process Wizard'
    
    res_model = fields.Char(required = True)
    res_ids = fields.Json(required = True)
    
    confirm_message = fields.Char()
    comment = fields.Html()
    
    button_id = fields.Many2one('approval.buttons', required=True)    
    action_type = fields.Selection(related='button_id.action_type')            
    fixed_return_state = fields.Char(related="button_id.return_state", string='Fixed Return Status')
    return_state = fields.Char('Return Status')    
    transfer_state = fields.Char('Transfer Status')    
    
    comment_required = fields.Boolean(compute = "_calc_comment_required")
    
    visible_selections = fields.Json(compute = "_calc_visible_selections")
    
    forward_user_id = fields.Many2one("res.users")
    
    @api.depends('button_id')
    def _calc_comment_required(self):
        for record in self:
            record.comment_required = record.button_id.comment == "required"
            
    @api.depends('button_id', 'res_model', 'res_ids')
    def _calc_visible_selections(self):
        for record in self:
            if record.action_type != "return" or record.fixed_return_state:
                record.visible_selections = None
                continue
            res = self.env[record.res_model].browse(record.res_ids) or self.env['approval.record']
            visible_selections = []
            for state in res._fields['state'].get_values(self.env):
                if state == res.state:
                    break
                visible_selections.append(state)
            record.visible_selections = visible_selections                            
                
    def process(self):
        records :ApprovalRecord = self.env[self.res_model].browse(self.res_ids)
        if self.comment:
            records._track_set_log_message(self.comment)  
        records._approval_comment = self.comment
        actions = []      
        kwargs = {}
        if self.action_type == "return":
            kwargs['return_state'] = self.return_state
            
        elif self.action_type == "cancel_workflow":
            kwargs['reason'] = self.comment

        elif self.action_type == "forward":
            kwargs['forward_user_id'] = self.forward_user_id.id

        elif self.action_type == "transfer":
            kwargs['transfer_state'] = self.transfer_state
                
        for record in records:                                                
            actions.append(record.approval_action_button(self.button_id.id, ignore_comment = True, **kwargs))
        return self.env['approval.record']._clean_actions(actions)
            
            
    
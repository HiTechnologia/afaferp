from odoo import models, _
from ast import literal_eval
from ..models.approval_record import ApprovalRecord
from typing import cast

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        approval_button_id = self.env.context.get('approval_button_id')
        action = super().action_send_mail()
        if approval_button_id:
            approval_button = self.env['approval.buttons'].browse(approval_button_id)
            if approval_button.action_type == 'email' and approval_button.email_next_action:
                record = cast(ApprovalRecord, self.env[self.model].browse(literal_eval(self.res_ids)))
                return record.approval_action_button(approval_button.id, next_action = True)                
                
        return action
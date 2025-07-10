from odoo import models, fields, api

class MailTemplate(models.Model):
    _inherit = "mail.template"
    
    _approval_automation_trigger = fields.Char(store = False, inverse = "_approval_trigger_set_defaults", groups=fields.NO_ACCESS)
    
    @api.onchange('model_id')
    def _approval_trigger_set_defaults(self, from_name_create=False):
        if self.model_id:
            approval_automation_trigger = self.sudo()._approval_automation_trigger or self._context.get('approval_automation_trigger')
            
            if approval_automation_trigger == 'on_enter_approval':
                self.body_html = self.env.ref("oi_workflow.approval_notification_default").arch
                self.partner_to = "{{ object.approval_partner_ids.ids }}"
                self.subject = "Approval | {{ object.get_title() }}"
                if not from_name_create:
                    self.name = f"Approval Notification | {self.model_id.name}"            
                
            elif approval_automation_trigger == 'on_reject':
                self.body_html = self.env.ref("oi_workflow.reject_notification_default").arch
                self.partner_to = "{{ object.document_user_id.partner_id.id or '' }}"
                self.subject = "Rejected | {{ object.get_title() }}"
                if not from_name_create:
                    self.name = f"Reject Notification | {self.model_id.name}"
                
            elif approval_automation_trigger == 'on_return':
                self.body_html = self.env.ref("oi_workflow.return_notification_default").arch
                self.partner_to = "{{ object.document_user_id.partner_id.id or '' }}"
                self.subject = "Returned | {{ object.get_title() }}"
                if not from_name_create:
                    self.name = f"Returned Notification | {self.model_id.name}"                
                    
    @api.model
    def name_create(self, name):
        res = super().name_create(name)
        if res and self._context.get('approval_automation_trigger'):
            template = self.browse(res[0])
            template._approval_trigger_set_defaults(from_name_create=True)
        return res
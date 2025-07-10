from odoo import fields, models, api
from odoo.tools.safe_eval import test_python_expr, safe_eval
from odoo.exceptions import ValidationError
from .approval_record import ApprovalRecord

import logging
_logger = logging.getLogger(__name__)

class ApprovalAutomation(models.Model):
    _name = 'approval.automation'
    _description = 'Approval Automation'
    _inherit = ['cache.mixin', 'xml_id.mixin']
    _order ='sequence,id'
    _auto_update_registry = True
    
    settings_id = fields.Many2one("approval.settings", required=True, ondelete = 'cascade')
    model = fields.Char(related='settings_id.model', readonly = True, store = True)
    model_id = fields.Many2one(related='settings_id.model_id', store = True, ondelete = 'cascade')
    sequence = fields.Integer()
    active = fields.Boolean(default = True)
    name = fields.Char(required=True, string='Description')    
    trigger = fields.Selection([
        ('on_submit', 'On Submit'),
        ('on_enter_approval', 'Enter Approval Status'),
        ('on_approve', 'On Approve'),
        ('on_approval', 'On Approval'),
        ('on_reject', 'On Reject'),
        ('on_return', 'On Return'),
        ('on_cancel', 'On Cancel'),
        ('on_draft', 'On Draft Reset'),
        ('on_forward', 'On Forward'),
        ('on_transfer', 'On Transfer'),
        ('on_state_updated', 'On Status Updated'),
        ('on_create', 'On creation'),
        ('on_committee_approval', 'On Committee Approval'),
        ], required=True)
    
    from_states = fields.Json('From Status')
    to_states = fields.Json('To Status')
    
    code = fields.Text('Python Code')
    
    template_ids = fields.Many2many('mail.template', string='Mail Templates')
    server_action_ids = fields.Many2many("ir.actions.server", string='Server Actions')
    
    filter_domain = fields.Char(string='Apply on')
    
    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.code:
                msg = test_python_expr(expr=record.code.strip(), mode="exec")
                if msg:
                    raise ValidationError(msg)
                
                
    def _process_survey(self, record: ApprovalRecord):
        pass
    
    def _process(self, record: ApprovalRecord):
        actions = []
        if self.filter_domain:
            if not record.filtered_domain(safe_eval(self.filter_domain or "[]")):
                return actions
                    
        self._process_survey(record)
        
        if self.code:
            localdict = record._get_eval_context()
            safe_eval(self.code.strip(), localdict, mode='exec', nocopy=True)
            action = localdict.get('action')
            if action:
                actions.append(action)
                
        for server_action_id in self.server_action_ids:
            action = server_action_id.with_context(active_model = record._name, active_ids = record.ids, active_id = record.id).run()                    
            if action:
                actions.append(action)
                
        for template in self.template_ids:
            template.send_mail(record.id)
                        
        return actions
                        
    def _register_hook(self):
        super()._register_hook()
        
        for automation_rule in self.with_context({}).search_fetch([], ["model", "trigger", "from_states", "to_states"]):
            Model = self.env.get(automation_rule.model)
            if Model is None:
                continue
            if not hasattr(Model, "_approval_trigger_methods"):
                _logger.warning("Model %s does not have _approval_trigger_methods", Model._name)
                continue
                        
            def make_approval_trigger_method(automation_rule_id, old_states, new_states):
            
                def approval_trigger_method(self):
                    automation_rule = self.env["approval.automation"].browse(automation_rule_id)
                    automation_rule._ensured_cached()
                    return automation_rule._process(self)             
                
                setattr(approval_trigger_method, f"_approval_{automation_rule.trigger}", (old_states, new_states))                
                return approval_trigger_method

            old_states = automation_rule.from_states and tuple(automation_rule.from_states) or None
            new_states = automation_rule.to_states and tuple(automation_rule.to_states) or None
                                    
            Model._approval_trigger_methods[automation_rule.trigger].append(make_approval_trigger_method(automation_rule.id, old_states, new_states))
            
            
    def _unregister_hook(self):
        super()._unregister_hook()
        for Model in self.env.registry.values():
            try:
                delattr(Model, "_approval_trigger_methods")
            except AttributeError:
                pass    
        
    def action_view_template(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("mail.action_email_template_tree_all")
        action.update({
            'domain' : [('model_id','=', self.model_id.id)],
            'context' : {
                'default_model_id' : self.model_id.id, 
                'approval_automation_trigger' : self.trigger,
                'search_default_name' : self.template_ids.name if len(self.template_ids) == 1 else False
            },            
        })
        return action
    
    def action_show_expression_editor(self):
        return self.model_id.action_show_expression_editor()
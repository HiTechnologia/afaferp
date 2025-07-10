from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

_button_classes = ['primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark', 'link']
_button_classes = [f"btn-{name}" for name in _button_classes] + [f"btn-outline-{name}" for name in _button_classes]

class ApprovalButtons(models.Model):
    _name = 'approval.buttons'
    _description = 'Approval Buttons'
    _inherit = ['cache.mixin', 'xml_id.mixin']
    _order ='sequence,id'
            
    settings_id = fields.Many2one("approval.settings", ondelete = 'cascade', required=True)
    config_id = fields.Many2one("approval.config", ondelete = 'cascade', string="Approval Status", inverse = "_onchage_config_id")
    model = fields.Char(related='settings_id.model', readonly = True, store = True, required=True, precompute = True)
    model_id = fields.Many2one(related='settings_id.model_id', readonly = True, store = True, required=True, precompute = True)
    sequence = fields.Integer()
    active = fields.Boolean(default = True)
    name = fields.Char(required=True, translate = True, string="Label")
    action_type = fields.Selection([
        ('approve', 'Approve document'),
        ('reject', 'Reject document'),
        ('return', 'Return to previous status'),
        ('cancel', 'Cancel document'),
        ('cancel_workflow', 'Cancel document (Workflow)'),
        ('draft', 'Reset to Draft'),
        ('forward', 'Forward approval to user'),
        ('transfer', 'Transfer to another status'),
        ('action', 'Server Action'),
        ('email', 'Send Email'),
        ('method', 'Call Method'),
        ], required=True)
    visible_to = fields.Selection([
        ('approval', 'Approval User'),
        ('requester', 'Document Requester'),
        ('domain', 'Filter Domain'),
    ])    
    method = fields.Char('Method Name', help="Method name to call on the record")
    visible_domain = fields.Char('Domain', help="Domain to filter users who can see this button")
    server_action_id = fields.Many2one("ir.actions.server")
    email_template_id = fields.Many2one("mail.template")
    email_wizard_form_id = fields.Many2one("ir.ui.view", domain = "[('type', '=', 'form'),('model', '=', 'mail.compose.message'),('mode','=', 'primary')]")
    email_next_action = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('return', 'Return'),
        ('cancel', 'Cancel'),
        ('draft', 'Reset to Draft'),
        ('action', 'Server Action'),
    ])
    return_state = fields.Char('Return Status')    
    group_ids = fields.Many2many('res.groups', string="Access Groups")
    button_class = fields.Selection([(name, name) for name in _button_classes])    
    confirm_message = fields.Char(translate = True)
    comment = fields.Selection([
     ('required', 'Required'),
     ('optional', 'Optional'),
    ])
    context = fields.Char(string='Context Value', default={}, required=True,
                          help="Context dictionary as Python expression, empty by default (Default: {})")
    invisible = fields.Char(string="Invisible Condition", help='Invisible Form Condition', compute = "_calc_invisible_condition",inverse = "_set_invisible_condition", store = True, readonly = False)
    icon = fields.Char(compute = "_calc_icon", store = True, readonly = False)
    
    states = fields.Json(string="Status", compute = "_compute_states", store = True, readonly = False, copy = False)
    
    run_as_superuser = fields.Boolean('Run as Superuser')
    
    show_process_wizard = fields.Boolean(compute = "_calc_show_process_wizard")
    
    hotkey = fields.Char('Keyboard shortcuts')
    
    validate_form = fields.Boolean(compute = "_compute_validate_form", store = True, readonly = False, help="Validate form fields before execute")

    voting_type = fields.Selection([('approve', 'Approve'), ('reject', 'Reject'), ('abstain', 'Abstain')], string='Voting Type')
    is_voting = fields.Boolean(related='config_id.is_voting')
        
    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.id}] {record.name}"
                            
    @api.onchange('config_id')
    def _onchage_config_id(self):
        for record in self:
            if record.config_id:
                record.settings_id = record.config_id.setting_id
    
    @api.depends('config_id')            
    def _compute_states(self):
        for record in self:
            if record.config_id:
                record.states = [record.config_id.state]
                
    @api.depends('action_type')
    def _compute_validate_form(self):
        for record in self:
            record.validate_form = record.action_type == "approve"
                
    @api.depends('action_type', 'return_state', 'comment')
    def _calc_show_process_wizard(self):
        for record in self:
            if record.comment:
                record.show_process_wizard = True
            elif record.action_type == "return" and not record.return_state:
                record.show_process_wizard = True
            elif record.action_type in ["forward", "transfer"]:
                record.show_process_wizard = True
            else:
                record.show_process_wizard = False                                
        
    @api.depends('visible_to', 'states')
    def _calc_invisible_condition(self):
        for record in self:
            invisible = []
            if record.visible_to == "domain":
                record.invisible = f"{record.id or '{BUTTON_ID}'} not in approval_visible_button_ids"
                continue
            if record.states:
                invisible.append(f"state not in {record.states}")
            if record.visible_to == "approval":
                invisible.append("not user_can_approve")
            elif record.visible_to == "requester":
                invisible.append("document_user_id != uid")            
            record.invisible = ' or '.join(invisible)
            
    def _set_invisible_condition(self):
        for record in self:
            if record.invisible and '{BUTTON_ID}' in record.invisible:
                record.invisible = record.invisible.replace('{BUTTON_ID}', str(record.id))
    
    @api.depends('action_type', 'server_action_id')
    def _calc_icon(self):
        for record in self:
            if record.server_action_id:
                if 'Excel' in record.server_action_id.code:
                    record.icon = "fa-file-excel-o"
                elif record.server_action_id.binding_type == "print":
                    record.icon = "fa-print"
                else:
                    record.icon = "fa-cog"
                continue
                
            record.icon = {
                "approve" : "fa-thumbs-up",
                "reject" : "fa-thumbs-down",
                "return" : "fa-reply",
                "cancel" : "fa-times",
                "cancel_workflow" : "fa-times-circle",
                'draft' : "fa-edit",
                'forward' : "fa-mail-forward",
                'transfer' : "fa-exchange",
                'action' : "fa-cog",
                "email" : "fa-envelope",
            }.get(record.action_type)            
    
    def _user_button_access(self):
        if not self.active:
            return False
        if not self.group_ids or self.env.is_superuser():
            return True
        return not set(self.group_ids.ids).isdisjoint(self.env.user._get_group_ids())
    
    
    def _is_invisible(self, record: models.BaseModel):
        self.ensure_one()
        if not self._user_button_access():
            return True
        if not self.invisible:
            return False
        field_names = [name for name, field in record._fields.items() if name in self.invisible and field.is_accessible(self.env)]
        return safe_eval(self.invisible, record.read(field_names, load = False)[0])        
    
    
    @api.constrains('action_type', 'model')
    def _check_cancel_state(self):
        for record in self:
            if record.action_type in ["cancel", "cancel_workflow"]:
                if not self.env[record.model]._get_cancel_state():
                    raise ValidationError(f"Cannot find cancel state in model {record.model}")

    @api.constrains('config_id', 'settings_id')
    def _check_config_id(self):
        for record in self:
            if record.config_id and record.config_id.setting_id != record.settings_id:
                raise UserError("config_id/settings_id mismatched")
            
    @api.constrains('action_type', 'method')
    def _check_method(self):
        for record in self:
            if record.method:
                if method := getattr(self.env[record.model], record.method, None):
                    if not callable(method):
                        raise UserError(f"Method {record.method} is not callable in model {record.model}")
                    if record.method.startswith("_"):
                        raise UserError(f"Method {record.method} is private in model {record.model}")
                else:
                    raise UserError(f"Method {record.method} not found in model {record.model}")

    def create(self, vals_list):
        res = super().create(vals_list)
        if 'voting_type' in vals_list:
            res.action_type = 'approve'
        return res 
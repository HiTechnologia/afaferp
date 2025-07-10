
from odoo import models, api, fields, _
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.exceptions import ValidationError
from odoo.fields import Command

import logging
_logger = logging.getLogger(__name__)

class ApprovalConfig(models.Model):
    _name = 'approval.config'
    _inherit = ['cache.mixin', 'xml_id.mixin']
    _description = 'Approval Workflow Settings'
    _order = 'sequence,id'
    _rec_names_search = ['name', 'state']
    
    @api.model
    def _get_sequence(self):
        model_id = self._context.get("default_model_id")
        ((max_sequence,),)= self._read_group([('model_id','=', model_id)],[],['sequence:max'])
        return (max_sequence or 0) + 1        
            
    model_id = fields.Many2one('ir.model', string='Object', required = True, ondelete='cascade')
    setting_id = fields.Many2one("approval.settings", compute = '_calc_setting_id')
    model = fields.Char(related='model_id.model', readonly = True, store = True)
    model_name = fields.Char(related='model_id.name', readonly = True)

    state = fields.Char(required = True, copy = False, string="Status")
    name = fields.Char(required = True, translate = True)
    active = fields.Boolean(default = True)
    sequence = fields.Integer(required = True, copy = False, default = _get_sequence)    
    
    group_ids = fields.Many2many('res.groups', string='Approval Groups', required = True, relation='approval_config_group_ids_rel')
    
    user_python_code = fields.Char()
        
    condition = fields.Text(string='Required Condition', default = 'True', required = True )
                        
    schedule_activity = fields.Boolean('Schedule Activity', default = True)
    schedule_activity_field_id = fields.Many2one('ir.model.fields')
    schedule_activity_days = fields.Integer('Activity Days')
                
    button_ids = fields.One2many("approval.buttons", "config_id", copy = True)
        
    escalation_ids = fields.One2many('approval.escalation', 'config_id')
    escalation_count = fields.Integer(compute = "_calc_escalation_count")
        
    tag_ids = fields.Many2many('state.tags', string='Tags')
    auto_approve = fields.Boolean('Automatic Approval', help= 'Auto approve if can approve this status')
    
    default_mail_template_body = fields.Char(compute = "_calc_default_mail_template")
    default_reject_mail_template_body = fields.Char(compute = "_calc_default_mail_template")
    
    committee = fields.Boolean('Committee Approval')
    committee_limit = fields.Integer()
    committee_vote_percentage = fields.Float(string='Approval Vote Percentage', default=50)

    user_ids = fields.Many2many('res.users')

    is_voting = fields.Boolean('Voting')
    
    _sql_constraints = [
        ('state_uniq', 'unique (model_id, state)', 'The state should be unique !'),
        ('name_uniq', 'unique (model_id, name)', 'The name should be unique !'),       
    ]    
    
    @api.onchange('committee')
    def _onchange_committee(self):
        self.is_voting = False

    @api.depends('escalation_ids')
    def _calc_escalation_count(self):
        for record in self:
            record.escalation_count = len(record.escalation_ids)
    
    @api.depends_context('lang')
    @api.depends('state','name')    
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} ({record.state})"
    
    @api.depends('model')
    def _calc_setting_id(self):
        for record in self:
            record.setting_id = self.env["approval.settings"].get(record.model)
    
    @api.depends_context('lang')
    def _calc_default_mail_template(self):
        for record in self:
            record.default_mail_template_body = self.env.ref("oi_workflow.approval_notification_default").arch
            record.default_reject_mail_template_body = self.env.ref("oi_workflow.reject_notification_default").arch
                        
    @api.constrains('condition')
    def _check_condition(self):
        for record in self:
            if record.condition:
                msg = test_python_expr(expr=record.condition.strip(), mode="eval")
                if msg:
                    raise ValidationError(msg)   
                    
    @api.constrains('user_python_code')
    def _check_user_python_code(self):
        for record in self:
            if record.user_python_code:
                msg = test_python_expr(expr=record.user_python_code.strip(), mode="exec")
                if msg:
                    raise ValidationError(msg)                                        
        
    @api.returns('self')
    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('state', f"{self.state}_copy")
        default.setdefault('name', _("%s (copy)") % (self.name or ''))
        return super(ApprovalConfig, self).copy(default = default)
                                                                                                                                                                            
    def _get_next(self, record):
        if not self:
            model_id = self.env['ir.model']._get_id(record._name)            
            records = self.search_cached([('model_id','=', model_id), ('active','=', True)])
            return records[:1]._next(record)
        return self._next(record, True)
    
    def _next(self, record, force = False):
        if not self:
            return self
        
        self.ensure_one()
                
        if not force:
            try:
                result = safe_eval(self.condition, record._get_eval_context(approval_state_id = self))
            except Exception as ex:
                _logger.error("Error evaluating workflow condition %s" % [record, self.state] )
                _logger.error(str(ex))
                result = False
                
            if result:
                return self
        
        records = self.search_cached([('model_id','=', self.model_id.id), ('active','=', True)])
        next_index = records.ids.index(self.id) + 1
        return records[next_index : next_index + 1]._next(record)  
    
    
    @api.model
    def _update_approval_activity(self, limit = 50):
        self._remove_invalid_approval_activity()
        for model_id, states in self._read_group([('schedule_activity','=', True)],['model_id'],['state:array_agg']):            
            offset = 0
            while records := self.env[model_id.model].search([('state','in', states)], limit = limit, offset = offset):
                records._reschedule_approval_activity()
                offset += limit
                self.env.cr.commit()            
                
    @api.model
    def _remove_invalid_approval_activity(self):        
        for model, record_ids,activity_ids in self.env['mail.activity']._read_group([('activity_type_id','=', self.env.ref('oi_workflow.activity_type_approval').id)], ['res_model'], ['res_id:array_agg','id:recordset']):            
            [[approval_states]] = self._read_group([('schedule_activity','=', True),('model','=', model)],[],['state:array_agg'])
            records = self.env[model].search([('id','in', record_ids),('state','not in', approval_states)])
            if records:
                activity_ids.filtered(lambda a: a.res_id in records.ids).unlink()
                            
        

    def action_view_escalation(self):        
        action =  {
            'type' : 'ir.actions.act_window',
            'name' : _('Escalations'),
            'res_model' : 'approval.escalation',
            'view_mode' : 'list,form',
            'domain' : [('config_id','=', self.id)],
            'context' : {
                    'default_active' : True, 
                    'default_config_id' : self.id,
                    'default_model_id' : self.model_id.id,
                    'default_name' : f"{self.model_id.name}: {self.name} Escalation", 
                    'default_trigger' : 'on_time', 
                    'default_trg_date_id' : self.env['ir.model.fields']._get(self.model, 'last_state_update').id, 
                    'default_filter_domain' : [('state','=', self.state)],
                    'active_test' : False
                },            
            }           
        if self.escalation_count == 1:
            action.update({
                'res_id' : self.escalation_ids.id,
                'view_mode' : 'form'
            })
        return action
    
    def action_show_expression_editor(self):   
        return self.model_id.action_show_expression_editor()
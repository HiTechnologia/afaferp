
from odoo import models, fields, api, _

class ApprovalSettings(models.Model):
    _name = 'approval.settings'
    _inherit = ['cache.mixin', 'xml_id.mixin']
    _description = 'Approval Workflow Model Settings'
    _rec_name = 'model'
    _order = 'sequence,id'
        
    model_id = fields.Many2one('ir.model', string='Object', required = True, ondelete='cascade', domain = [('field_id.name','=', 'state'), ('transient','=', False)])    
    model = fields.Char(related='model_id.model', store = True, readonly = True)
    model_name = fields.Char(related='model_id.name', readonly = True)    
    sequence = fields.Integer()
    state_ids = fields.One2many('approval.settings.state', 'settings_id', context={'active_test' : False}, string="Static Statuses")    
    approval_count = fields.Integer(compute = '_calc_approval_count')    
    automation_count = fields.Integer(compute = '_calc_automation_count')
    button_count = fields.Integer(compute = '_calc_button_count')
    
    show_action_approve_all = fields.Boolean(default = True)    
    show_status_duration_tracking = fields.Boolean(default = True)
    approval_all_groups = fields.Many2many('res.groups', relation="approval_settings_approval_all_groups_rel")
            
    dynamic_statusbar_visible = fields.Boolean(default = True)
    
    static_states = fields.Boolean("Custom Static Statuses", inverse="_set_static_states")
    
    advance = fields.Boolean()
    
    _sql_constraints = [
        ('model_uniq', 'unique (model_id)', 'The model should be unique !'),
    ]            
    
    def _default_states(self):
        model = self.model_id.model
        sequence = 0
        res =[]
        for state, name in self.env[model]._before_approval_states():
            sequence +=1
            res.append({
                'state' : state,
                'name' : name,
                'type' : 'before',
                'sequence' : sequence,
                'settings_id' : self.id
                })
        for state, name in self.env[model]._after_approval_states():
            sequence +=1
            res.append({
                'state' : state,
                'name' : name,
                'type' : 'after',
                'sequence' : sequence,
                'reject_state' : state=='rejected',
                'settings_id' : self.id
                })           
        return res     
        
    def reset_states(self):
        self.state_ids.unlink()
        
        lang_vals_list = {}
        for lang, __ in self.env['res.lang'].get_installed():
            lang_vals_list[lang] = self.with_context(lang = lang)._default_states()
        
        for lang, vals_list in lang_vals_list.items():
            for vals in vals_list:                 
                record = self.state_ids.filtered(lambda approval_state_id: approval_state_id.state == vals['state'])
                if not record:
                    record.with_context(lang = lang).create(vals)
                else:
                    record.with_context(lang = lang).name = vals['name']
                    
    @api.depends('model_id')
    def _calc_approval_count(self):
        for record in self:
            record.approval_count = self.env['approval.config'].search_count([('model_id', '=', record.model_id.id)])
                        
    @api.depends('model_id')
    def _calc_automation_count(self):
        for record in self:
            record.automation_count = self.env['approval.automation'].search_count([('settings_id','=', record.id)])
            
    @api.depends('model_id')
    def _calc_button_count(self):
        for record in self:
            record.button_count = self.env['approval.buttons'].search_count([('settings_id','=', record.id)])
        
        
    def action_view_approval(self):
        model_id = self.model_id.id
        return  {
            'type' : 'ir.actions.act_window',
            'name' : _('Approval Status'),
            'res_model' : 'approval.config',
            'view_mode' : 'list,form',
            'context' : {'default_model_id' : model_id, 'active_test' : False, 'hide_model' : True},
            'domain' : [('model_id','=', model_id)]
            }
        
    def action_view_automation(self):
        return  {
            'type' : 'ir.actions.act_window',
            'name' : _('Automation'),
            'res_model' : 'approval.automation',
            'view_mode' : 'list,form',
            'context' : {'default_settings_id' : self.id, 'active_test' : False, 'hide_model' : True},
            'domain' : [('settings_id','=', self.id)]
            }     
        
    def action_view_buttons(self):
        return  {
            'type' : 'ir.actions.act_window',
            'name' : _('Buttons'),
            'res_model' : 'approval.buttons',
            'view_mode' : 'list,form',
            'context' : {'default_settings_id' : self.id, 'active_test' : False, 'search_default_filter_config_id_not_set' : 1, 'hide_model' : True},
            'domain' : [('settings_id','=', self.id)],
            'views' : [(self.env.ref("oi_workflow.view_approval_buttons_list_approval_settings").id, 'list'),(False, 'form')]
            }              
                    
    @api.model
    def get(self, model):
        return self.search_cached([('model','=', model)])
        
    def is_show_action_approve_all(self):
        if not self:
            return
        if not self.show_action_approve_all:
            return False
        if not self.approval_all_groups:
            return True
        return not set(self.approval_all_groups.ids).isdisjoint(self.env.user._get_group_ids())
    
    
    def _set_static_states(self):
        for record in self:
            if not record.static_states and record.state_ids:
                record.state_ids.unlink()
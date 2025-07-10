from odoo import _, api, fields, models
from odoo.exceptions import UserError

class IrModel(models.Model):
    _inherit = 'ir.model'

    is_approval_record = fields.Boolean('Approval Record', inverse = "_create_approval_settings")
    
    def _reflect_model_params(self, model):
        vals = super()._reflect_model_params(model)
        vals['is_approval_record'] = isinstance(model, self.pool['approval.record'])
        return vals    
    
    @api.model
    def _instanciate(self, model_data):        
        model_class = super()._instanciate(model_data)
        if model_data.get('is_approval_record') and model_class._name != 'approval.record':
            parents = model_class._inherit or []
            parents = [parents] if isinstance(parents, str) else parents
            for name in ['mail.thread', 'mail.activity.mixin']:
                if name in parents:
                    parents.remove(name)
            model_class._inherit = parents + ['approval.record']
        return model_class        
    
    def _create_approval_settings(self):
        for record in self:
            if record.is_approval_record and record.state == "manual":
                if not self.env['approval.settings'].search([('model_id','=', record.id)]):
                    self.env['approval.settings'].create({'model_id' : record.id})
                    
    @api.onchange('is_approval_record')
    def _onchange_is_approval_record(self):
        if self.is_approval_record:
            self.is_mail_thread = True
            self.is_mail_activity = True
            
    def action_show_expression_editor(self):   
        return {
            "type" : "ir.actions.act_window",
            'res_model' : 'model.expression.editor',
            'view_mode' : 'form',
            'target' : 'new',
            'context' : {
                'default_model' : self.model
            }
        }            
        
    def action_view_fields(self):   
        return {
            "type" : "ir.actions.act_window",
            'res_model' : 'ir.model.fields',
            'name': _("Fields"),
            'view_mode' : 'list,form',
            'domain' : [('model_id','=', self.id)],
            'context' : {
                'default_model_id' : self.id
            }
        }                    
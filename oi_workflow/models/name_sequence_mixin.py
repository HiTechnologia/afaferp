from odoo import models, fields, api, _
from odoo.tools import create_unique_index

class NameSequenceMixin(models.AbstractModel):
    _name = 'name.sequence.mixin'
    _description = 'Name Sequence Mixin'
    _auto_sequence_create = False

    name = fields.Char(string='Number', required=True, copy= False, default = lambda self: self._get_default_name())        
    
    @api.model
    def _get_default_name(self):
        return self.env._("New")
    
    @api.model
    def _get_name_sequence_code(self, vals):
        return self._name
            
    @api.model_create_multi
    @api.returns('self', lambda value:value.id)
    def create(self, vals_list):
        default_name = self.default_get(['name']).get('name')
        for vals in vals_list:
            if vals.get('name', default_name) == default_name:
                vals['name'] = self.env['ir.sequence'].next_by_code(self._get_name_sequence_code(vals))            
        return super().create(vals_list) 
    
    def _get_sequence_vals(self):
        prefix = ''.join([desc[0].upper() for desc in self._description.split()])
        return {
            'name': self._description,
            'code': self._get_name_sequence_code({}),
            'padding': 4,
            'prefix': f'{prefix}/%(year)s/',
            'company_id': False,
            'use_date_range': True
        }
    
    def _create_auto_sequence(self):
        if self._abstract or not self._auto_sequence_create:
            return
        vals = self._get_sequence_vals()
        if not self.env['ir.sequence'].sudo().search([('code', '=', vals['code'])], limit=1):
            self.env['ir.sequence'].sudo().create(vals)

    def init(self):
        super().init()
        self._create_auto_sequence()
        if not self._abstract and self._table:
            expressions = ['name']
            if 'company_id' in self._fields and self._fields['company_id'].store:
                expressions.append('company_id')
            create_unique_index(self._cr, f"{self._table}_name_unique", self._table, expressions)    
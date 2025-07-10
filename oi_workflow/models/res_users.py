'''
Created on Sep 18, 2018

@author: Zuhair Hammadi
'''
from odoo import models, fields, api

class User(models.Model):
    _inherit = 'res.users'
    
    wkf_groups_ids = fields.Many2many('res.groups', compute = '_calc_wkf_groups_ids')
    
    @api.depends('groups_id')
    def _calc_wkf_groups_ids(self):
        field = 'active_groups_ids' in self and 'active_groups_ids' or 'groups_id'
        for record in self:
            record.wkf_groups_ids = record[field]
            
                
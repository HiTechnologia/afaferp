from odoo import models, api

class Many2manyAttachmentResIDMixin(models.AbstractModel):
    'Many2many Attachment auto set res_id/res_field'
    _name = 'many2many.attachment.res_id.mixin'
    _description = 'Many2many Attachment ResID Mixin'
    
    def _set_many2many_attachment_res_id(self, vals):
        for name in vals:
            field = self._fields[name]
            if field.type == "many2many" and field.comodel_name == "ir.attachment":
                for record in self:
                    record[name].res_id = self.id
                    record[name].res_field = name
                
    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list)
        
        for record, vals in zip(records, values_list):
            record._set_many2many_attachment_res_id(vals)
        
        return records

    def write(self, vals):
        res = super().write(vals)
        self._set_many2many_attachment_res_id(vals)
        return res
from odoo import models, fields

class ExternalIDMixin(models.AbstractModel):
    _name = 'xml_id.mixin'
    _description = 'External ID Mixin'
        
    xml_id = fields.Char(string="External ID", compute='_compute_xml_id')
    
    def _compute_xml_id(self):
        xml_ids = self._get_external_ids()
        for record in self:
            record.xml_id = ','.join(xml_ids.get(record.id, []))

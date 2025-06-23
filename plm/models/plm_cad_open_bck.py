import logging
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class PlmCadOpenBck(models.Model):
    _name = "plm.cad.open.bck"
    _description = "Opens made by the client"
    _order = 'id DESC'

    plm_backup_doc_id = fields.Many2one('plm.backupdoc', 'Backup Document Reference')
    userid = fields.Many2one('res.users', 'Related User')
    document_id = fields.Many2one('ir.attachment', 'Related Document')
    rel_doc_rev = fields.Integer(related='document_id.engineering_revision', string="Revision", store=True)
    pws_path = fields.Char('PWS Path')
    hostname = fields.Char('Hostname')
    operation_type = fields.Char('Operation Type')
    
    def name_get(self):
        result = []
        for r in self:
            if r.document_id and r.userid:
                name = "%s - R:%s - [%s]" % (r.document_id.engineering_code, r.document_id.engineering_revision, r.userid.display_name)
            else:
                name = "Error"
            result.append((r.id, name))
        return result

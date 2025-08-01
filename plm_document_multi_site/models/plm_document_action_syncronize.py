import logging
import datetime
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

#env["plm.document.action.syncronize"].syncronize()


class PlmDocumentActionSyncronize(models.Model):
    _name = "plm.document.action.syncronize"
    _description = "Plm Document Action Syncronize"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    plm_remote_server_id = fields.Many2one('plm.remote.server',
                                           string="Server to perform the Update",
                                           help='This is the server in witch we will perform the syncronizations')
    ir_attachment_id = fields.Many2one('ir.attachment',
                                       string="Attachment to Syncronize")

    done = fields.Boolean(string="Syncronization is done ?")

    action = fields.Selection([('pull', 'Pull'),
                               ('push', 'Push')])

    @api.model
    def syncronize(self, document_ids=[]):
        ir_attachment_processed = []
        ir_attachment_error = []
        domain_push = [('done', '=', False),
                       ('action', '=', 'push')]
        if document_ids:
            domain_push.append(('ir_attachment_id', 'in', document_ids)),
        for plm_document_action_syncronize_id in self.search(domain_push,
                                                             order='id desc'):
            if not plm_document_action_syncronize_id.done:
                ir_attachment_id = plm_document_action_syncronize_id.ir_attachment_id
                if ir_attachment_id.id not in ir_attachment_processed:
                    if plm_document_action_syncronize_id.plm_remote_server_id.push_document_to_remote(ir_attachment_id):
                        plm_document_action_syncronize_id.done = True
                        ir_attachment_processed.append(ir_attachment_id.id)
                    else:
                        ir_attachment_error.append(ir_attachment_id.id)
                else:
                    plm_document_action_syncronize_id.done = True
            self.env.cr.commit()
        ir_attachment_processed = []
        domain_pull = [('done', '=', False),
                       ('action', '=', 'pull')]
        if document_ids:
            domain_pull.append(('ir_attachment_id', 'in', document_ids))
        if ir_attachment_error:
            domain_pull.append(('ir_attachment_id', 'not in', ir_attachment_error))
        for plm_document_action_syncronize_id in self.search(domain_pull,
                                                             order='id desc'):
            ir_attachment_id = plm_document_action_syncronize_id.ir_attachment_id
            if ir_attachment_id.id not in ir_attachment_processed:
                if plm_document_action_syncronize_id.plm_remote_server_id.pull_document_to_odoo(plm_document_action_syncronize_id.ir_attachment_id):
                    plm_document_action_syncronize_id.done = True
                    ir_attachment_processed.append(ir_attachment_id.id)
            else:
                plm_document_action_syncronize_id.done = True
            self.env.cr.commit()

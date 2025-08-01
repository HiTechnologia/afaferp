from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import time


class PlmCheckout(models.Model):
    _name = 'plm.checkout'
    _description = 'Document that are locked from someone'

    userid = fields.Many2one('res.users',
                             _('Related User'),
                             index=True,
                             ondelete='cascade')
    hostname = fields.Char(_('hostname'),
                           index=True,
                           size=64)
    hostpws = fields.Char(_('PWS Directory'),
                          index=True,
                          size=1024)
    documentid = fields.Many2one('ir.attachment',
                                 _('Related Document'),
                                 index=True,
                                 ondelete='cascade')
    rel_doc_rev = fields.Integer(related='documentid.engineering_revision',
                                 string="Revision",
                                 store=True)

    preview = fields.Binary(related='documentid.preview')

    _sql_constraints = [
        ('documentid', 'unique (documentid)', _('The documentid must be unique !'))
    ]

    
    def name_get(self):
        result = []
        for r in self:
            if not r.documentid or not r.userid:
                name = 'unknown'
            else:
                document_name = r.documentid.name if r.documentid.engineering_code is False else r.documentid.engineering_code
                name = "%s .. [%s]" % (document_name[:10], r.userid.name[:8])
            result.append((r.id, name))
        return result

    @api.model
    def _adjustRelations(self, childDocIds, userid=False):
        docRelType = self.env['ir.attachment.relation']
        if userid:
            docRelBrwsList = docRelType.search([('child_id', 'in', childDocIds), ('userid', '=', False)])
        else:
            docRelBrwsList = docRelType.search([('child_id', 'in', childDocIds)])
        if docRelBrwsList:
            values = {'userid': userid}
            docRelBrwsList.write(values)

    @api.model_create_multi
    def create(self, vals):
        for vals_dict in vals:
            docBrws = self.env['ir.attachment'].browse(vals_dict['documentid'])
            values = {'engineering_writable': True}
            if not docBrws.sudo(True).write(values):
                logging.warning("create : Unable to check-out the required document (" + str(docBrws.engineering_code) + "-" + str(docBrws.engineering_revision) + ").")
                raise UserError(_("Unable to check-out the required document (" + str(docBrws.engineering_code) + "-" + str(docBrws.engineering_revision) + ")."))
            self._adjustRelations([docBrws.id])
        newCheckoutBrws = super().create(vals)
        docBrws.message_post(body=_('Checked-Out ID %r' % (newCheckoutBrws.id)))
        return newCheckoutBrws

    
    def unlink(self):
        documentType = self.env['ir.attachment']
        docids = []
        for checkObj in self:
            if not checkObj.documentid:
                continue
            if checkObj.documentid.has_error:
                raise UserError(f"Unable to check-in due to an error on saving document [{checkObj.documentid.engineering_code} rev {checkObj.documentid.engineering_revision}] with error {checkObj.documentid.getLastError()}")
            checkObj.documentid.engineering_writable = False
            values = {'engineering_writable': False}
            docids.append(checkObj.documentid.id)
            if not documentType.browse([checkObj.documentid.id]).write(values):
                logging.warning("unlink : Unable to check-in the document (" + str(checkObj.documentid.engineering_code) + "-" + str(checkObj.documentid.engineering_revision) + ").\n You can't change writable flag.")
                raise UserError(_("Unable to Check-In the document (" + str(checkObj.documentid.engineering_code) + "-" + str(checkObj.documentid.engineering_revision) + ").\n You can't change writable flag."))
        self._adjustRelations(docids, False)
        dummy = super(PlmCheckout, self).unlink()
        if dummy:
            for doc_id in documentType.browse(docids):
                doc_id.message_post(body=_('Checked-In'))
        return dummy


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

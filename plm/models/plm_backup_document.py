from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging
import os
import stat


class PlmBackupDocument(models.Model):
    """
        Only administrator is allowed to remove elements by this table
    """
    _name = 'plm.backupdoc'
    _description = "manage your document back up"

    userid = fields.Many2one('res.users',
                             _('Related User'))
    existingfile = fields.Char(_('Physical Document Location'),
                               size=1024)
    documentid = fields.Many2one('ir.attachment',
                                 _('Related Document'))
    engineering_revision = fields.Integer(related="documentid.engineering_revision",
                                string=_("Revision"),
                                store=True)
    engineering_state = fields.Selection(related="documentid.engineering_state",
                                         string=_("Status"),
                                         store=True)
    document_name = fields.Char(related="documentid.engineering_code",
                                string=_("Stored Name"),
                                store=True)
    printout = fields.Binary(_('Printout Content'))
    preview = fields.Binary(_('Preview Content'))
    orig_data_fstore = fields.Char(string="Original FStore Name")

    def name_get(self):
        result = []
        for r in self:
            if r.documentid and r.userid:
                name = "%s - R:%s - [%s]" % (r.documentid.engineering_code, r.documentid.engineering_revision, r.userid.display_name)
            else:
                name = "Error"
            result.append((r.id, name))
        return result

    def remaining_unlink(self):
        super(PlmBackupDocument, self).unlink()
    
    def unlink(self):
        documentType = self.env['ir.attachment']
        for plm_backup_document_id in self:
            if self.env.context:
                if not self.env.user.has_group('plm.group_plm_admin'):
                    logging.warning("unlink : Unable to remove the required documents. You aren't authorized in this context.")
                    raise UserError(_("Unable to remove the required document.\n You aren't authorized in this context."))
            if plm_backup_document_id.documentid:
                currentname = plm_backup_document_id.documentid.store_fname
                if plm_backup_document_id.existingfile != currentname:
                    fullname = os.path.join(documentType._get_filestore(), plm_backup_document_id.existingfile)
                    if os.path.exists(fullname):
                        os.chmod(fullname, stat.S_IWRITE)
                        os.unlink(fullname)
                    else:
                        logging.warning("unlink : Unable to remove the document (" + str(plm_backup_document_id.documentid.name) + "-" + str(plm_backup_document_id.documentid.revisionid) + ") from backup set. You can't change writable flag.")
                        raise UserError(_("Unable to remove the document (" + str(plm_backup_document_id.documentid.name) + "-" + str(plm_backup_document_id.documentid.revisionid) + ") from backup set.\n It isn't a backup file, it's original current one."))
                else:
                    logging.warning('Prevent to delete the active File %r' % currentname)
                    continue
            super(PlmBackupDocument, plm_backup_document_id).unlink()

    @api.model
    def getLastBckDocumentByUser(self, doc_id):
        for obj in self.search([
            ('documentid', '=', doc_id.id),
            ('create_uid','=',self.env.user.id),
            ], order='create_date DESC', limit=1):
            return obj
        return self

    @api.model
    def getLastBckDocument(self, doc_id):
        for obj in self.search([
            ('documentid', '=', doc_id.id),
            ], order='create_date DESC', limit=1):
            return obj
        return self

class BackupDocWizard(models.TransientModel):
    """
        This class is called from an action in xml located in plm.backupdoc.
        Pay attention! You can restore also confirmed, released and obsoleted documents!!!
    """

    _name = 'plm.backupdoc_wizard'
    _description = "Back up document wizard"

    
    def action_restore_document(self):
        ctx = self.env.context.copy()
        ctx['check'] = False
        documentId = False
        plm_backupdoc_ids = self.env.context.get('active_ids', [])
        plm_backupdoc = self.env['plm.backupdoc']
        ir_attachment = self.env['ir.attachment']
        if len(plm_backupdoc_ids) > 1:
            raise UserError(_('Restore Document Error'), _("You can restore only a document at a time."))
        for plm_backupdoc_id in plm_backupdoc.browse(plm_backupdoc_ids):
            ir_attachment_bck_id = plm_backupdoc_id.documentid
            if not ir_attachment_bck_id.ischecked_in():
                raise UserError("""Unable to restore check-out document !!.\nMake check-in with user [ %s ]"""  % (ir_attachment_bck_id.checkout_user))
            values = {'printout': plm_backupdoc_id.printout,
                      'preview': plm_backupdoc_id.preview,
                      }
            if ir_attachment_bck_id:
                documentId = ir_attachment_bck_id.id
                write_res = ir_attachment_bck_id.sudo().with_context(ctx).write(values)
                sql = """
                UPDATE IR_ATTACHMENT SET store_fname = '%s' where id = %s
                """ % (plm_backupdoc_id.existingfile, ir_attachment_bck_id.id)
                self.env.cr.execute(sql)
                if write_res:
                    logging.info('[action_restore_document] Updated document %r' % (documentId))
                else:
                    logging.warning('[action_restore_document] Updated document failed for %r' % (documentId))
            else:
                # Note that if I don't have a document I can't relate it to it's component
                # User have to do it hand made
                values.update({'engineering_state': 'draft',
                               'engineering_revision': plm_backupdoc_id.engineering_revision,
                               'name': plm_backupdoc_id.document_name,
                               }
                              )
                documentId = ir_attachment.sudo().create(values)
                if documentId:
                    logging.info('[action_restore_document] Created document %r' % (documentId))
                else:
                    logging.warning('[action_restore_document] Create document failed for %r' % (documentId))
        
        action_vals = self.env['ir.actions.act_window']._for_xml_id('plm.plm_action_document_form')
        domain = safe_eval(action_vals.get('domain', "[]"))
        domain = expression.AND([domain, [('id', 'in', [documentId])]])
        action_vals['domain'] = domain
        return action_vals

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

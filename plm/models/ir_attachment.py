import copy
import json
#
import logging
import os
import random
import shutil
import string
from datetime import datetime

import odoo.tools as tools
import time
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.addons.plm.models.plm_mixin import (PLM_NO_WRITE_STATE, RELEASED_STATUS,
                                              CONFIRMED_STATUS, OBSOLATED_STATUS,
                                              START_STATUS)
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from pickle import FALSE

_logger = logging.getLogger(__name__)


def random_name():
    random.seed()
    d = [random.choice(string.ascii_letters) for _x in range(20)]
    return "".join(d)


class IrAttachment(models.Model):
    _name = 'ir.attachment'
    _description = "Ir Attachment"
    _inherit = ['ir.attachment', 'revision.plm.mixin']

    printout = fields.Binary(_('Printout Content'),
                             help=_("Print PDF content."))
    printout_name = fields.Char(_('Printout Name'), compute="_getPrintoutName")
    preview = fields.Image(_('Preview Content'),
                           max_width=1920,
                           max_height=1920,
                           attachment=False)

    checkout_user = fields.Char(string=_("Checked-Out to"),
                                compute='_get_checkout_state')
    
    
    is_checkout = fields.Boolean(_('Is Checked-Out'),
                                 compute='_is_checkout',
                                 store=False)
    linkedcomponents = fields.Many2many('product.product',
                                        'plm_component_document_rel',
                                        'document_id',
                                        'component_id',
                                        _('Linked Parts'),
                                        ondelete='cascade')
    is_linkedcomponents = fields.Boolean('Is Linked Components',
                                         compute='_compute_linkedcomponents')

    document_rel_count = fields.Integer(compute='_get_n_rel_doc')

    datas = fields.Binary(string='File Content (base64))',
                          compute='_compute_datas',
                          inverse='_inverse_datas')

    document_type = fields.Selection([('other', _('Other')),
                                      ('2d', _('2D')),
                                      ('3d', _('3D')),
                                      ('pr', _('Presentation')),
                                      ],
                                     compute='_compute_document_type',
                                     store=True,
                                     string=_('Document Type'))
    desc_modify = fields.Text(_('Modification Description'), default='')
    is_plm = fields.Boolean('Is A Plm Document',
                            help=_(
                                "If the flag is set, the document is managed by the plm module, and imply its backup at each save and the visibility on some views."))
    attachment_revision_count = fields.Integer(compute='_attachment_revision_count')
    first_source_path = fields.Char("Source path of the first time save")
    cad_name = fields.Char("Cad Name")
    is_library = fields.Boolean("Is Library file",
                                default=False)
    library_path = fields.Char("File library path")

    must_update_from_cad = fields.Boolean("Must Update form CAD",
                                          compute="_compute_must_update_from_cad",
                                          help="""When this flag is enabled the 2d document must be updated in order to guaranteey the update betwin 2d and 3d document""")
    preview_related = fields.Image(max_height=1920, max_width=1920,
                                   string=_("Child Parent Preview"))


    def _compute_must_update_from_cad(self):
        ir_attachment_relation = self.env['ir.attachment.relation']
        for ir_attachment in self:
            ir_attachment.must_update_from_cad = False
            if ir_attachment.document_type == '2d':
                ir_attachment.must_update_from_cad = not ir_attachment_relation.is_2d_ok(ir_attachment)
            elif ir_attachment.document_type == 'pr':
                ir_attachment.must_update_from_cad = not ir_attachment_relation.is_pr_ok(ir_attachment)

    def _getPrintoutName(self):
        for ir_attachment_id in self:
            ir_attachment_id.printout_name = f"{ir_attachment_id.engineering_code}_{ir_attachment_id.engineering_revision}.pdf"

    def getPrintoutUrl(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/plm/ir_attachment_printout/{self.id}"

    def download_printout(self):
        return {'type': 'ir.actions.act_url',
                'url': self.getPrintoutUrl(),
                'target': 'new',
                }

    @property
    def actions(self):
        return {'reactivate': self.action_reactivate,
                'obsolete': self.action_obsolete,
                'release': self.action_release,
                'confirm': self.action_confirm,
                'draft': self.action_draft}

    def isLatestRevision(self):
        for docBrws in self:
            lastdocIds = self._getlastrev(docBrws.id)
            for lastDocId in lastdocIds:
                if lastDocId == docBrws.id:
                    return True
        return False

    @api.model
    def check(self, mode, values=None):
        if self.env.context.get('plm_avoid_recursion'):
            return True
        if self.env.is_superuser():
            return True
        if self:
            self.env['ir.attachment'].flush_model()
            self._cr.execute('SELECT  id, is_plm, public FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
            attachment_id_toCheck = []
            for attachment_id, is_plm, public in self._cr.fetchall():
                if public and mode == 'read':
                    continue
                if is_plm:
                    if self.env.user.has_group('plm.group_plm_integration_user'):
                        continue
                    if self.env.user.has_group('plm.group_plm_view_user') and mode == 'read':
                        continue
                    if self.env.user.has_group('plm.group_plm_readonly_released') and mode == 'read':
                        continue
                    if self.env.user.has_group('plm.group_plm_admin'):
                        continue
                    raise UserError("You are managing a document that dose not belong to any PLM group.")
                else:
                    attachment_id_toCheck.append(attachment_id)
            #
            if attachment_id_toCheck:
                super().with_context(plm_avoid_recursion=True).check(mode, values)

    def get_checkout_user(self):
        lastDoc = self._getlastrev(self.ids)
        if lastDoc:
            for docBrws in self.env['plm.checkout'].search([('documentid', '=', lastDoc[0])]):
                return docBrws.userid
        return False

    def _is_checkedout_for_me(self):
        """
            Get if given document (or its latest revision) is checked-out for the requesting user
        """
        userBrws = self.get_checkout_user()
        if userBrws:
            if userBrws.id == self.env.uid:
                return True
        return False

    def _getlastrev(self, resIds):
        return self.browse(resIds)._get_last_rev_no_browser()

    def _get_last_rev_no_browser(self):
        result = []
        for objDoc in self:
            doc_ids = self.search([('engineering_code', '=', objDoc.engineering_code)],
                                  order='engineering_revision DESC')
            for doc in doc_ids:
                result.append(doc.id)
                break
            if not doc_ids:
                logging.warning('[_getlastrev] No documents are found for object with engineering_code: "%s"' % (
                    objDoc.engineering_code))
        return list(set(result))

    def browseLastRev(self):
        self.ensure_one()
        out = self.search([('engineering_code', '=', self.engineering_code)],
                          order='engineering_revision DESC',
                          limit=1)
        for obj in out:
            return obj
        return out

    def GetLastNamesFromID(self):
        """
            get the last rev
        """
        newIds = self._getlastrev(self.ids)
        return self.browse(newIds).mapped('name')

    @api.model
    def _isDownloadableFromServer(self, server_name):
        """
            Check in the file is downloadable from server
            this function is implemented in the plm_document_multi_site module
        """
        return False, ''

    def _data_get_files(self,
                        listedFiles=([], []),
                        forceFlag=False,
                        local_server_name=True):
        """
            Get Files to return to Client
        """
        if isinstance(local_server_name, bool):
            local_server_name = 'odoo'
        local_server_name_errors = []
        result = []
        datefiles, listfiles = listedFiles
        for objDoc in self:
            if local_server_name != 'odoo':
                responce, message = objDoc._isDownloadableFromServer(local_server_name)
                if not responce:
                    local_server_name_errors.append(message)
            timeDoc = self.getLastTime(objDoc.id)
            timeSaved = time.mktime(timeDoc.timetuple())
            try:
                isCheckedOutToMe = objDoc._is_checkedout_for_me()
                if not (objDoc.name in listfiles):
                    datas = False
                    if local_server_name == 'odoo':
                        datas = objDoc.datas
                    result.append((objDoc.id,
                                   objDoc.name,
                                   datas,
                                   isCheckedOutToMe,
                                   timeDoc))
                else:
                    if forceFlag:
                        isNewer = True
                    else:
                        timefile = time.mktime(datetime.strptime(str(datefiles[listfiles.index(objDoc.name)]),
                                                                 '%Y-%m-%d %H:%M:%S').timetuple())
                        isNewer = (timeSaved - timefile) > 5
                    if (isNewer and not (isCheckedOutToMe)):
                        datas = False
                        if local_server_name == 'odoo':
                            datas = objDoc.datas
                        result.append((objDoc.id,
                                       objDoc.name,
                                       datas,
                                       isCheckedOutToMe,
                                       timeDoc))
                    else:
                        result.append((objDoc.id,
                                       objDoc.name,
                                       False,
                                       isCheckedOutToMe,
                                       timeDoc))
            except Exception as ex:
                logging.error(
                    "_data_get_files : Unable to access to document (" + str(
                        objDoc.engineering_code) + "). Error :" + str(ex))
                result.append((objDoc.id,
                               objDoc.name,
                               False,
                               True,
                               self.getServerTime()))
        if local_server_name != 'odoo':
            if local_server_name_errors:
                return True, local_server_name_errors
            else:
                return False, result
        return result

    def _inverse_datas(self):
        super(IrAttachment, self)._inverse_datas()
        for ir_attachment_id in self:
            try:
                if ir_attachment_id.is_plm and self.env.context.get("backup", True):
                    if self.env['plm.backupdoc'].search_count(
                        [('orig_data_fstore', '=', ir_attachment_id.store_fname)]) == 0:
                        file_name = random_name() + "OdooPLM_BCK"
                        folder_name = self._full_path(file_name[0:4])
                        try:
                            os.makedirs(folder_name)
                        except:
                            logging.warning("Directory %s olready present " % folder_name)
                            pass
                        to_file = os.path.join(folder_name, file_name)
                        shutil.copyfile(self._full_path(ir_attachment_id.store_fname),
                                        to_file)
                        self.env['plm.backupdoc'].create({'userid': self.env.uid,
                                                          'existingfile': os.path.join(file_name[0:4], file_name),
                                                          'documentid': ir_attachment_id.id,
                                                          'printout': ir_attachment_id.printout,
                                                          'orig_data_fstore': ir_attachment_id.store_fname,
                                                          'preview': ir_attachment_id.preview})
            except Exception as ex:
                logging.error("Unable to copy file for backup Error: %r" % ex)

    @api.model
    def _explodedocs(self, oid, kinds, listed_documents=[], recursion=True):
        result = []
        documentRelation = self.env['ir.attachment.relation']

        def getAllDocumentChildId(fromID, kinds):
            docRelBrwsList = documentRelation.search([('parent_id', '=', fromID), ('link_kind', 'in', kinds)])
            for child in docRelBrwsList:
                idToAdd = child.child_id.id
                if idToAdd not in result:
                    result.append(idToAdd)
                    if recursion:
                        getAllDocumentChildId(idToAdd, kinds)

        getAllDocumentChildId(oid, kinds)
        return result

    @api.model
    def getRelatedOneLevelLinks(self, doc_id, kinds):
        result = []
        for link_kind in kinds:
            if link_kind == 'RfTree':
                result.extend(self.getRelatedRfTree(doc_id, False))
            elif link_kind == 'LyTree':
                result.extend(self.getRelatedLyTree(doc_id))
            elif link_kind == 'HiTree':
                result.extend(self.getRelatedHiTree(doc_id, False))
            elif link_kind == 'PkgTree':
                result.extend(self.getRelatedPkgTree(doc_id))
            else:
                logging.warning('getRelatedOneLevelLinks cannot find link_kind %r' % (link_kind))
        return list(set(result))

    @api.model
    def getRelatedLyTree(self, 
                         doc_id, 
                         optional_return_type=['3d'],
                         getOnyChkOut=False):
        out = []
        if not doc_id:
            logging.warning('Cannot get links from %r document' % (doc_id))
            return []
        if not isinstance(doc_id, models.Model): 
            doc_brws = self.browse(doc_id)
        else:
            doc_brws = doc_id
            doc_id = doc_brws.id 
        parent_doc_type = doc_brws.document_type
        to_search = [('link_kind', 'in', ['LyTree']),
                     '|',
                     ('parent_id', '=', doc_id),
                     ('child_id', '=', doc_id)]
        doc_rel_ids = self.env['ir.attachment.relation'].search(to_search)
        for doc_rel_id in doc_rel_ids:
            if parent_doc_type == '3d':
                if doc_rel_id.parent_id.id == doc_id and doc_rel_id.child_id.document_type == '2d':
                    out.append(doc_rel_id.child_id.id)
                elif doc_rel_id.child_id.id == doc_id and doc_rel_id.parent_id.document_type == '2d':
                    out.append(doc_rel_id.parent_id.id)
            elif parent_doc_type == '2d':
                if doc_rel_id.parent_id.id == doc_id and doc_rel_id.child_id.document_type in optional_return_type:
                    out.append(doc_rel_id.child_id.id)
                elif doc_rel_id.child_id.id == doc_id and doc_rel_id.parent_id.document_type in optional_return_type:
                    out.append(doc_rel_id.parent_id.id)
        return list(set(out))

    @api.model
    def getRelatedPrTree(self,
                         root_doc_id,
                         recursion=False,
                         getOnyChkOut=False):
        out = []

        def _getRelatedPrTree(doc_id):
            if not doc_id:
                logging.warning('Cannot get links from %r document' % (doc_id))
                return []
            doc_brws = self.browse(doc_id)
            doc_type = doc_brws.document_type
            to_search = [('link_kind', 'in', ['LyTree']),
                         '|',
                         ('parent_id', '=', doc_id),
                         ('child_id', '=', doc_id)]
            doc_rel_ids = self.env['ir.attachment.relation'].search(to_search)
            for doc_rel_id in doc_rel_ids:
                good_id = None
                if doc_type in ['3d', '2d']:
                    if doc_rel_id.parent_id.id == doc_id and doc_rel_id.child_id.document_type == 'pr':
                        good_id = doc_rel_id.child_id
                    if doc_rel_id.child_id.id == doc_id and doc_rel_id.parent_id.document_type == 'pr':
                        good_id = doc_rel_id.parent_id
                elif doc_type == 'pr':
                    if doc_rel_id.parent_id.id == doc_id and doc_rel_id.child_id.document_type == '3d':
                        good_id = doc_rel_id.child_id
                    elif doc_rel_id.child_id.id == doc_id and doc_rel_id.parent_id.document_type == '3d':
                        good_id = doc_rel_id.parent_id
                if good_id and good_id.i not in out:
                    if getOnyChkOut:
                        if not good_id.is_checkout:
                            continue
                    out.append(good_id.id)
                    if recursion:
                        for recursion_id in _getRelatedPrTree(good_id.id):
                            if recursion_id not in out:
                                out.append(recursion_id)

        _getRelatedPrTree(root_doc_id)
        return list(set(out))

    @api.model
    def getRelatedRfTree(self, doc_id, recursion=True, evaluated=False):
        if not evaluated:
            evaluated = []
        out = []
        if not doc_id:
            logging.warning('Cannot get links from %r document' % (doc_id))
            return []
        to_search = [('link_kind', 'in', ['RfTree']), ('parent_id', '=', doc_id)]
        doc_rel_ids = self.env['ir.attachment.relation'].search(to_search)
        if doc_id in evaluated:
            logging.warning('Document %r already found in RfTree evaluated %r' % (doc_id, evaluated))
            return out
        evaluated.append(doc_id)
        for doc_rel_id in doc_rel_ids:
            if doc_rel_id.child_id.id == doc_id:
                out.append(doc_rel_id.parent_id.id)
                if recursion:
                    out.extend(self.getRelatedRfTree(doc_rel_id.parent_id.id, recursion, evaluated))
            else:
                out.append(doc_rel_id.child_id.id)
                if recursion:
                    out.extend(self.getRelatedRfTree(doc_rel_id.child_id.id, recursion, evaluated))
        return list(set(out))

    @api.model
    def getRelatedPkgTree(self, doc_id):
        out = []
        if not doc_id:
            logging.warning('Cannot get links from %r document' % (doc_id))
            return []
        to_search = [('link_kind', 'in', ['PkgTree']),
                     ('parent_id', '=', doc_id)]
        doc_rel_ids = self.env['ir.attachment.relation'].search(to_search)
        for doc_rel_id in doc_rel_ids:
            out.append(doc_rel_id.child_id.id)
        return list(set(out))

    @api.model
    def getRelatedHiTree(self,
                         doc_id, 
                         recursion=True, 
                         getRftree=False,
                         getOnyChkOut=False):
        '''
            Get children HiTree documents
        '''
        out = []

        def _getRelatedHiTree(doc_id, 
                              recursion, 
                              getRftree):
            if not doc_id:
                logging.warning('Cannot get links from %r document' % (doc_id))
                return []
            children_attachment_ids = self.env['ir.attachment.relation'].search([
                ('link_kind', '=', 'HiTree'),
                ('parent_id', '=', doc_id)])
            for child_attachment_id in children_attachment_ids:
                child_id = child_attachment_id.child_id.id
                if child_id in out:
                    logging.warning('Document %r document already found' % (doc_id))
                    continue
                out.append(child_id)
                if recursion:
                    _getRelatedHiTree(child_id,
                                      recursion,
                                      getRftree)
            if getRftree:
                out.extend(self.getRelatedRfTree(doc_id, 
                                                 recursion=True, 
                                                 evaluated=[]))

        _getRelatedHiTree(doc_id, recursion, getRftree)
        return out

    @api.model
    def getRelatedAllLevelDocumentsTree(self, starting_doc_id):
        outList = []
        evaluated = []

        def recursion(doc_id):
            if not doc_id:
                return []
            if doc_id not in evaluated:
                evaluated.append(doc_id)
            else:
                return []
            outList.append(doc_id)
            doc_brws = self.browse(doc_id)
            rf_tree_doc_ids = self.getRelatedRfTree(doc_id, recursion=False)
            for rf_tree_doc_id in rf_tree_doc_ids:
                outList.extend(recursion(rf_tree_doc_id))
            outList.extend(rf_tree_doc_ids)
            if doc_brws.is3D():
                ly_tree_doc_ids = self.getRelatedLyTree(doc_id)
                outList.extend(ly_tree_doc_ids)
                outList.extend(self.getRelatedPkgTree(doc_id))
                doc_ids = self.getRelatedHiTree(doc_id, recursion=False)
                for child_doc_id in doc_ids:
                    recursion(child_doc_id)
            elif doc_brws.is2D():
                model_doc_ids = self.getRelatedLyTree(doc_id)
                for model_doc_id in model_doc_ids:
                    recursion(model_doc_id)
            return []

        recursion(starting_doc_id.id)
        return list(set(outList))

    def computeDownloadStatus(self,
                              hostname,
                              pws_path,
                              latest=False):
        """
            compute ir_attachment data suitable for client
            :hostname host name
            :pws_path path to Private Work Space folder
            :latest get the latest version of the files
            :return: list of ir_attachment properties as dictionary [{<property>}]
                    {
                    id
                    code
                    revision
                    file_name
                    write_date
                    is_library
                    library_path
                    is_out_by_me
                    check_out_user_name
                    collectable
                    isCheckedOutToMe
                    engineering_writable
                    check_out_user
                    state
                    zip_ids
                    is_last_version
                    }
        """
        out = []
        computed = []
        for ir_attachment_id in self:
            #
            if latest:
                ir_attachment_id = ir_attachment_id.get_latest_version()[0]
            #
            active_attachment_id = ir_attachment_id.id
            if active_attachment_id in computed:
                continue
            computed.append(active_attachment_id)
            #
            is_collectable = False
            isCheckedOutToMe, checkOutUser = ir_attachment_id.checkoutByMeWithUser()
            if not isCheckedOutToMe:
                is_collectable = ir_attachment_id.isCollectable(hostname,
                                                                pws_path)
            #
            out_dict = ir_attachment_id.get_open_attachment_data_out()
            out_dict.update({
                        'collectable': is_collectable,
                        'isCheckedOutToMe': isCheckedOutToMe,
                        'engineering_writable': isCheckedOutToMe,
                        'check_out_user': checkOutUser,
                        'state': ir_attachment_id.engineering_state,
                        'zip_ids': self.getRelatedPkgTree(active_attachment_id),
                        'is_last_version': ir_attachment_id.isLatestRevision(),
                        })
            out.append(out_dict)
        return out

    def get_open_attachment_data_out(self):
        self.ensure_one()
        return {
            'id':self.id,
            'code': self.engineering_code,
            'revision': self.engineering_revision,
            'file_name': self.name,
            'write_date': self.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'is_library': self.is_library,
            'library_path':self.library_path,
            'is_out_by_me': self.isCheckedOutByMe(),
            'check_out_user_name':self.checkout_user,
            }

    def isCollectable(self, hostname, pws_path):
        self.ensure_one()
        out = True
        if self.isCheckedOutByMe(): out = False
        plm_cad_open = self.sudo().env['plm.cad.open'].getLastCadOpenByUser(self, self.env.user)
        if plm_cad_open:
            if plm_cad_open.hostname == hostname and plm_cad_open.pws_path == pws_path:
                last_revision_id = self.browseLastRev()
                if last_revision_id != last_revision_id:
                    if last_revision_id.isCheckedOutByMe():
                        out = False
        return out

    def _data_check_files(self, targetIds, listedFiles=(), forceFlag=False, retDict=False, hostname='', hostpws=''):
        result = []
        listfiles = []
        if len(listedFiles) > 0:
            _datefiles, listfiles = listedFiles
        for objDoc in self.browse(targetIds):
            outId = objDoc.id
            isCheckedOutToMe, checkOutUser = objDoc.checkoutByMeWithUser()
            datas_fname = objDoc.name
            if datas_fname in listfiles:
                if forceFlag:
                    isNewer = True
                else:
                    isNewer = objDoc.checkNewer()
                collectable = isNewer and not isCheckedOutToMe
            else:
                collectable = True
            objDatas = False
            try:
                objDatas = objDoc.datas
            except Exception as ex:
                logging.error(
                    'Document with "id": %s  and "engineering_code": %s may contains no data!!         Exception: %s' % (
                        outId, objDoc.engineering_code, ex))
            if (objDoc.file_size < 1) and (objDatas):
                file_size = len(objDoc.datas)
            else:
                file_size = objDoc.file_size
            if retDict:
                result.append({'docIDList': outId,
                               'nameFile': objDoc.name,
                               'fileSize': file_size,
                               'collectable': collectable,
                               'isCheckedOutToMeLastRev': isCheckedOutToMe,
                               'checkOutUser': checkOutUser,
                               'state': objDoc.engineering_state})
            else:
                result.append((outId, objDoc.name, file_size, collectable, isCheckedOutToMe, checkOutUser))
            if collectable:
                self.browse(outId).setupCadOpen(hostname, hostpws, 'open')
        return list(set(result))

    def copy(self, defaults={}):
        """
            Overwrite the default copy method
        """
        defaults['engineering_state'] = START_STATUS
        defaults['engineering_writable'] = True
        if not self.is_plm:
            defaults['engineering_code'] = False
            newDocBrws = super(IrAttachment, self).copy(defaults)
        else:
            documentRelation = self.env['ir.attachment.relation']
            docBrwsList = documentRelation.search([('parent_id', '=', self.id)])
            previous_name = self.engineering_code
            if 'engineering_code' not in defaults:
                new_name = 'Copy of %s' % previous_name
                documents = self.search([('engineering_code', '=', new_name)], order='engineering_revision')
                if len(documents) > 0:
                    new_name = '%s (%s)' % (new_name, len(documents) + 1)
                defaults['engineering_code'] = new_name
            newDocBrws = super(IrAttachment, self).copy(defaults)
            if newDocBrws:
                newDocBrws.message_post(body=_('Copied starting from : %s.' % previous_name))
            for brwEnt in docBrwsList:
                documentRelation.create({
                    'parent_id': newDocBrws.id,
                    'child_id': brwEnt.child_id.id,
                    'configuration': brwEnt.configuration,
                    'link_kind': brwEnt.link_kind,
                })
        return newDocBrws

    @api.model
    def _iswritable(self, oid):
        if not oid.type == 'binary':
            logging.warning(
                "_iswritable : Part (" + str(oid.name) + "-" + str(
                    oid.engineering_revision) + ") not writable as hyperlink.")
            return False
        if oid.engineering_state not in (START_STATUS):
            logging.warning(
                "_iswritable : Part (" + str(oid.name) + "-" + str(oid.engineering_revision) + ") in status ; " + str(
                    oid.engineering_state) + ".")
            return False
        if not oid.name:
            logging.warning(
                "_iswritable : Part (" + str(oid.name) + "-" + str(
                    oid.engineering_revision) + ") without Engineering P/N.")
            return False
        return True

    def newVersion(self):
        """
            create a new version of the document (to WorkFlow calling)
        """
        if self.NewRevision(self.id) is not None:
            return True
        return False

    @api.model
    def NewRevision(self, docId, newBomDocumentRevision=True):
        """
            create a new revision of the document
        """

        def setupSourceBoms(tmpObject, newObj):
            logging.info('Start cleaning old revision Boms')
            for componentBrws in self.linkedcomponents:
                for bomBrws in componentBrws.bom_ids:
                    if bomBrws.source_id.id == tmpObject.id:
                        for bomLineBrws in bomBrws:
                            if bomLineBrws.source_id.id == tmpObject.id:
                                bomLineBrws.write({'source_id': newObj.id})
                        bomBrws.write({'source_id': newObj.id})
                        logging.info(
                            'Bom ID %r update with new source ID %r / %r' % (bomBrws.id, tmpObject.id, newObj.id))

        newID = None
        newRevIndex = False
        ctx = self.env.context.copy()
        ctx['check'] = False
        if isinstance(docId, (list, tuple)):
            if len(docId) > 1:
                docId, newBomDocumentRevision = docId
            else:
                docId = docId[0]

        for tmpObject in self.browse(docId):
            latestIDs = self.GetLatestIds([(tmpObject.engineering_code, tmpObject.engineering_revision, False)])
            for oldObject in self.browse(latestIDs):
                oldObject.with_context(ctx).write({'engineering_state': 'undermodify'})
                defaults = {}
                newRevIndex = int(oldObject.engineering_revision) + 1
                defaults['engineering_code'] = oldObject.engineering_code
                defaults['engineering_revision'] = newRevIndex
                defaults['engineering_writable'] = True
                defaults['engineering_state'] = START_STATUS
                res = super(IrAttachment, oldObject).copy(defaults)
                newID = res.id
                res.engineering_revision_user = self.env.uid
                res.engineering_revision_date = datetime.now()
                res.engineering_release_user = False
                res.engineering_release_date = False
                res.engineering_workflow_user = False
                res.engineering_workflow_date = False
                if not newBomDocumentRevision:
                    setupSourceBoms(tmpObject, res)
                oldObject.message_post(body=_('Created : New Revision.'))
                break
            break
        return (newID, newRevIndex)

    def Clone(self, defaults={}):
        """
            create a new copy of the document
        """
        exitValues = {}
        newID = self.copy(defaults)
        if newID is not None:
            newEnt = self.browse(newID)
            exitValues['_id'] = newID
            exitValues['engineering_code'] = newEnt.engineering_code
            exitValues['engineering_revision'] = newEnt.engineering_revision
        return exitValues

    @api.model
    def CheckSaveUpdate(self, documents, default=None):
        """
            Save or Update Documents
            @hasToBeSaved: client use this flag to know if document and preview has to be saved
        """
        retValues = []
        for document in documents:
            hasToBeSaved = False
            if not ('engineering_code' in document) or ('engineering_revision' not in document):
                document['documentID'] = False
                document['hasSaved'] = False  # Not info --> not to be saved
                continue
            docBrwsList = self.search([('engineering_code', '=', document['engineering_code']),
                                       ('engineering_revision', '=', document['engineering_revision'])],
                                      order='engineering_revision')
            existingID = False
            if not docBrwsList:
                hasToBeSaved = True  # Yes info + not present --> to be saved
            else:
                for existingBrws in docBrwsList:
                    existingID = existingBrws.id
                    if existingBrws.isCheckedOutByMe():
                        hasToBeSaved = True
                        # Need to force update if in check-out because this flag is also used to
                        # know if this document has to be saved as BOM. Save bom procedure goes recursively to remove
                        # BOM lines and then BOMs. So checked-out document will don't have it's BOM.
                        # If this flag is a True the BOM will be recreated.
                    break
            document['documentID'] = existingID
            document['hasSaved'] = hasToBeSaved
            retValues.append(document)
        return retValues

    @api.model
    def SaveOrUpdate(self, documents, default=None):
        """
            Save or Update Documents
        """
        retValues = []
        for document in documents:
            hasSaved = False
            hasUpdated = False
            if not ('engineering_code' in document) or ('engineering_revision' not in document):
                document['documentID'] = False
                document['hasSaved'] = hasSaved
                document['hasUpdated'] = hasUpdated
                continue
            docBrwsList = self.search([('engineering_code', '=', document['engineering_code']),
                                       ('engineering_revision', '=', document['engineering_revision'])],
                                      order='engineering_revision')
            if not docBrwsList:
                existingID = self.create(document).id
                hasSaved = True
            else:
                for existingBrws in docBrwsList:
                    existingID = existingBrws.id
                    if existingBrws.isCheckedOutByMe():
                        hasSaved = True
                        # Need to force update if in check-out because this flag is also used to
                        # know if this document has to be saved as BOM. Save bom procedure goes recursively to remove
                        # BOM lines and then BOMs. So checked-out document will don't have it's BOM.
                        # If this flag is a True the BOM will be recreated.
                    break
            document['documentID'] = existingID
            document['hasSaved'] = hasSaved
            document['hasUpdated'] = hasUpdated
            retValues.append(document)
        return retValues

    @api.model
    def RegMessage(self, request, default=None):
        """
            Registers a message for requested document
        """
        oid, message = request
        self.browse([oid]).message_post(body=_(message))
        return False

    @api.model
    def UpdateDocuments(self, documents, default=None):
        """
            Save or Update Documents
        """
        ret = True
        for document in documents:
            oid = document['documentID']
            del (document['documentID'])
            ret = ret and self.browse([oid]).write(document, check=True)
        return ret

    def CleanUp(self, default=None):
        """
            Remove faked documents
        """
        self.env.cr.execute("delete from ir_attachment where store_fname=NULL and type='binary'")
        return True

    @api.model
    def QueryLast(self, request=([], []), default=None):
        """
            Query to return values based on columns selected.
        """
        expData = []
        queryFilter, columns = request
        if len(columns) < 1:
            return expData
        if 'engineering_revision' in queryFilter:
            del queryFilter['engineering_revision']
        docBrwsList = self.search(queryFilter, order='engineering_revision')
        if len(docBrwsList) > 0:
            tmpData = docBrwsList.export_data(columns)
            if 'datas' in tmpData:
                expData = tmpData['datas']
        return expData

    def ischecked_in(self):
        """
            Check if a document is checked-in
        """
        checkoutType = self.env['plm.checkout']
        for document in self:
            if checkoutType.search([('documentid', '=', document.id)]):
                logging.warning(
                    _("The document %s - %s has not checked-in" % (
                    str(document.engineering_code), str(document.engineering_revision))))
                return False
        return True

    def commonWFAction(self, writable, state, check):
        """
            :writable set writable flag for component
            :state define new product state
            :check do state verification in component write
        """
        self.with_context(check=check)._commonWFAction(writable, state, check)

    def _commonWFAction(self, writable, state, check):
        """
            :writable set writable flag for component
            :state define new product state
            :check do state verification in component write
        """
        for ir_attachment_id in self:
            ir_attachment_id.with_context(check=False).move_to_state(state)
            if ir_attachment_id.is3D():
                pkg_doc_ids = self.getRelatedPkgTree(ir_attachment_id.id)
                self.browse(pkg_doc_ids).commonWFAction(writable, state, check)

    def action_draft(self):
        """
            action to be executed for Draft state
        """
        self.commonWFAction(True, START_STATUS, False)
        return False

    def action_confirm(self):
        """
            action to be executed for Confirm state
        """
        self.commonWFAction(False, CONFIRMED_STATUS, False)
        return False

    def action_release(self):
        """
            release the object
        """
        to_release = self.env['ir.attachment']
        for oldObject in self:
            if oldObject.ischecked_in():
                to_release += oldObject
        if to_release:
            to_release.commonWFAction(False, RELEASED_STATUS, False)
        return False

    def action_obsolete(self):
        """
            obsolete the object
        """
        self.commonWFAction(False, OBSOLATED_STATUS, False)
        return False

    def action_reactivate(self):
        """
            reactivate the object
        """
        for attachment_id in self:
            if attachment_id.ischecked_in():
                attachment_id.with_context(check=False).move_to_state(START_STATUS)
        return False

    def blindwrite(self, vals):
        """
            blind write for xml-rpc call for recovering porpouse
            DO NOT USE FOR COMMON USE !!!!
        """
        ctx = self.env.context.copy()
        ctx['check'] = False
        return self.with_context(ctx).write(vals)

    #   Overridden methods for this entity
    @api.model
    def _get_filestore(self):
        document_path = tools.config.get('document_path')
        filestore = ''
        if document_path:
            filestore = os.path.join(document_path, self.env.cr.dbname)
        else:
            filestore = tools.config.filestore(self._cr.dbname)
        try:
            os.makedirs(filestore)
        except OSError as ex:
            if ex.errno not in [13, 17]:
                raise ex
            if ex.errno == 13:
                logging.warning(_("Permission denied for folder %r." % (str(filestore))))
                return ''
        return filestore

    def check_unique(self):
        for ir_attachment_id in self:
            if self.search_count([('engineering_code', '=', ir_attachment_id.name),
                                  ('engineering_revision', '=', ir_attachment_id.engineering_revision),
                                  ('document_type', 'in', ['2d', '3d'])]) > 1:
                raise UserError(_('Document Already in the system'))

    def plm_sanitize(self, vals):
        all_keys = self._fields
        if isinstance(vals, dict):
            valsKey = list(vals.keys())
            for k in valsKey:
                if k not in all_keys:
                    del vals[k]
            return vals
        else:
            out = []
            for k in vals:
                if k in all_keys:
                    out.append(k)
            return out

    def _check_unique_document(self, vals):
        if self.env.context.get('odooPLM'):
            if 'name' in vals and 'engineering_code' in vals:
                if self.search_count([('engineering_code', '=', vals['engineering_code']),
                                      ('name', 'not ilike', vals['name'])]):
                    raise Exception(
                        _(f"You are trying to create a new attachment [{vals['name']}] with the some engineering code [{vals['engineering_code']}]"))

    @api.model_create_multi
    def create(self, vals):
        if not self.env.context.get('odooPLM'):
            return super(IrAttachment, self).create(vals)
        to_create_vals = []
        for vals_dict in vals:
            if 'res_model' not in vals_dict:
                vals_dict['res_model'] = 'plm.access'
                vals_dict['res_id'] = self.env.ref('plm.plm_basic_access_model').id
            if 'engineering_state' not in vals:
                vals_dict['engineering_state'] = START_STATUS
            vals_dict['is_plm'] = True
            vals_dict.update(self.checkMany2oneClient(vals_dict))
            vals_dict = self.plm_sanitize(vals_dict)
            vals_dict['engineering_workflow_user'] = self.env.uid
            vals_dict['engineering_workflow_date'] = datetime.now()
            to_create_vals.append(vals_dict)
            self._check_unique_document(vals_dict)
        res = super(IrAttachment, self).create(to_create_vals)
        res.with_context(create=True).check_unique()
        return res

    def update_component_preview(self):
        for ir_attachment_id in self:
            if ir_attachment_id.document_type == '3d' and ir_attachment_id.preview:
                to_update = {}
                for product_tmpl in ir_attachment_id.linkedcomponents:
                    to_update[product_tmpl.engineering_revision] = product_tmpl
                if to_update:
                    to_update[max(to_update)].image_1920 = self.preview

    def write(self, vals):
        if not self.env.context.get('odooPLM'):
            return super(IrAttachment, self).write(vals)
        check = self.env.context.get('check', True)
        if check:
            self.writeCheckDatas(vals)
        #
        self._check_unique_document(vals)
        #
        vals.update(self.checkMany2oneClient(vals))
        vals = self.plm_sanitize(vals)
        res = super(IrAttachment, self).write(vals)
        #
        self.check_unique()
        #
        return res

    def read(self, fields=[], load='_classic_read', *k, **kw):
        try:
            customFields = [field.replace('plm_m2o_', '') for field in fields if field.startswith('plm_m2o_')]
            fields.extend(customFields)
            fields = list(set(fields))
            fields = self.plm_sanitize(fields)
            ctx = self.env.context.copy()
            plm_flag = ctx.get('odooPLM', False)
            if plm_flag:
                self = self.sudo()
            res = super(IrAttachment, self).read(fields=fields, load=load)
            res = self.readMany2oneFields(res, fields)
            return res
        except Exception as ex:
            raise ex

    def readMany2oneFields(self, readVals, fields):
        return self.env['product.product']._readMany2oneFields(self.env['ir.attachment'], readVals, fields)

    def checkMany2oneClient(self, vals):
        return self.env['product.product']._checkMany2oneClient(self.env['ir.attachment'], vals)

    @api.model
    def is_plm_state_writable(self):
        for customObject in self:
            if customObject.engineering_state in PLM_NO_WRITE_STATE:
                logging.info("state %r not in %r" % (customObject.engineering_state, PLM_NO_WRITE_STATE))
                return False
        return True

    def writeCheckDatas(self, vals):
        if 'datas' in list(vals.keys()) or 'engineering_code' in list(vals.keys()):
            for attachment_id in self:
                if not (self.env.user._is_admin() or self.env.user._is_superuser()):
                    if attachment_id.document_type and attachment_id.document_type.upper() in ['2D', '3D']:
                        if not attachment_id._is_checkedout_for_me():
                            raise UserError(
                                _("You cannot edit a file not in check-out by you! User ID %s" % (self.env.uid)))
                        if not attachment_id.is_plm_state_writable():
                            raise UserError(_("The active state does not allow you to make save action"))

    def getParentDocuments(self):
        parent_dict = {}
        for doc in self:
            parent_dict.setdefault(doc, [])
            att_rel_obj = self.env['ir.attachment.relation'].search([('child_id', '=', doc.id)])
            for record in att_rel_obj:
                parent_dict[doc].append((record.parent_id))
        return parent_dict

    def unlinkCheckDocumentRelations(self):
        ctx = self.env.context.copy()
        for checkObj in self:
            id_parents = checkObj.getParentDocuments()
            for child_doc, parent_docs in id_parents.items():
                if parent_docs:
                    msg = _('You cannot unlink a component child that is present in a related documents:\n')
                    for parent_doc in parent_docs:
                        msg += _('\t Engineering Name = %r   Engineering Revision = %r   Id = %r\n') % (
                        parent_doc.engineering_code, parent_doc.engineering_revision, parent_doc.id)
                    raise UserError(msg)

    def unlinkRestorePreviousDocument(self):
        for checkObj in self:
            docBrwsList = self.search([('engineering_code', '=', checkObj.engineering_code),
                                       ('engineering_revision', '=', checkObj.engineering_revision - 1)], limit=1)
            for oldObject in docBrwsList:
                oldObject.message_post(body=_('Removed : Latest Revision.'))
                values = {'engineering_state': RELEASED_STATUS}
                if not oldObject.with_context(check=False).write(values):
                    msg = 'Unlink : Unable to update state in old document Engineering Name = %r   Engineering Revision = %r   Id = %r' % (
                    oldObject.engineering_code, oldObject.engineering_revision, oldObject.id)
                    logging.warning(msg)
                    raise UserError(
                        _('Cannot restore previous document Engineering Name = %r   Engineering Revision = %r   Id = %r' % (
                        oldObject.engineering_code, oldObject.engineering_revision, oldObject.id)))
        return True

    def unlinkBackUp(self):
        for checkObj in self:
            docBrwsList = self.env['plm.backupdoc'].search([('documentid', '=', checkObj.id)])
            for oldObject in docBrwsList:
                oldObject.remaining_unlink()

    def unlink(self):
        for checkObj in self:
            checkObj.unlinkCheckDocumentRelations()
            checkObj.linkedcomponents.mapped("product_tmpl_id").unlinkCheckBomRelations()
            checkObj.linkedcomponents = False
            checkObj.unlinkRestorePreviousDocument()
            checkObj.unlinkBackUp()
        return super(IrAttachment, self).unlink()

    #   Overridden methods for this entity
    @api.model
    def _check_duplication(self, vals, ids=None, op='create'):
        engineering_code = vals.get('engineering_code', False)
        parent_id = vals.get('parent_id', False)
        ressource_parent_type_id = vals.get('ressource_parent_type_id', False)
        ressource_id = vals.get('ressource_id', 0)
        engineering_revision = vals.get('engineering_revision', 0)
        if op == 'write':
            for ir_attachment_id in self.browse(ids):
                if not engineering_code:
                    engineering_code = ir_attachment_id.engineering_code
                if not parent_id:
                    parent_id = ir_attachment_id.parent_id and ir_attachment_id.parent_id.id or False
                # TODO fix algo
                if not ressource_parent_type_id:
                    ressource_parent_type_id = ir_attachment_id.ressource_parent_type_id and ir_attachment_id.ressource_parent_type_id.id or False
                if not ressource_id:
                    ressource_id = ir_attachment_id.ressource_id and ir_attachment_id.ressource_id or 0
                docBrwsList = self.search([('id', '<>', ir_attachment_id.id),
                                           ('engineering_code', '=', engineering_code),
                                           ('parent_id', '=', parent_id),
                                           ('ressource_parent_type_id', '=', ressource_parent_type_id),
                                           ('ressource_id', '=', ressource_id),
                                           ('engineering_revision', '=', engineering_revision)])
                if docBrwsList:
                    return False
        if op == 'create':
            docBrwsList = self.search(SUPERUSER_ID,
                                      [('engineering_code', '=', engineering_code),
                                       ('parent_id', '=', parent_id),
                                       ('ressource_parent_type_id', '=', ressource_parent_type_id),
                                       ('ressource_id', '=', ressource_id),
                                       ('engineering_revision', '=', engineering_revision)])
            if docBrwsList:
                return False
        return True

    #   Overridden methods for this entity

    def _get_checkout_state(self):
        for ir_attachment_id in self:
            chechRes = self.getCheckedOut(ir_attachment_id.id, None)
            if chechRes:
                ir_attachment_id.checkout_user = str(chechRes[2])
            else:
                ir_attachment_id.checkout_user = ''

    def toggle_check_out(self):
        for ir_attachment_id in self:
            if ir_attachment_id.isCheckedOutByMe():
                if not ir_attachment_id._check_in():
                    raise UserError(
                        f"Unable to check out document with id {ir_attachment_id.id} check the log for more detais !!")
            else:
                if ir_attachment_id.is_checkout:
                    raise UserError(
                        f"Unable to check out. The owner of this document is {ir_attachment_id.checkout_user}")
                else:
                    ir_attachment_id.checkout("localhost", r"check/web")
        return True # this is for XmlRpc Calls

    @api.model
    def CheckIn(self, attrs):
        id = attrs.get('id')
        if id:
            docBrwsList = self.browse(id)
        else:
            engineering_code = attrs.get('engineering_code', '')
            engineering_revision = attrs.get('engineering_revision', False)
            docBrwsList = self.search([('engineering_code', '=', engineering_code),
                                       ('engineering_revision', '=', engineering_revision)])
        for docBrws in docBrwsList:
            docBrws._check_in()
            return docBrws.id
        return False

    def _check_in(self):
        checkOutId = self.isCheckedOutByMe()
        if not checkOutId:
            msg = """"Document %r is not in check out by user %r so cannot be checked-in""" % (
            self.id, self.env.user.id)
            logging.info(msg)
            return False
        if self.file_size <= 0 or not self.name:
            msg = 'Document %r has not document content so cannot be checked-in' % (self.id)
            logging.warning(msg)
            return False
        self.env['plm.checkout'].browse(checkOutId).unlink()
        return self.id

    @api.model
    def _is_checkout(self):
        for ir_attachment_id in self:
            _docName, _docRev, chekOutUser, _hostName = self.env['ir.attachment'].getCheckedOut(ir_attachment_id.id,
                                                                                                None)
            if chekOutUser:
                ir_attachment_id.with_context(check=False).is_checkout = True
            else:
                ir_attachment_id.with_context(check=False).is_checkout = False

    def getFileExtension(self, docBrws):
        fileExtension = ''
        name = docBrws.name
        if name:
            fileExtension = '.' + name.split('.')[-1]
        return fileExtension

    @api.depends('name')
    def _compute_document_type(self):
        configParamObj = self.env['ir.config_parameter'].sudo()
        file_exte_2d_param = configParamObj._get_param('file_exte_type_rel_2D')
        file_exte_3d_param = configParamObj._get_param('file_exte_type_rel_3D')
        file_exte_pr_param = configParamObj._get_param('file_exte_type_rel_PR')

        extensions2D = []
        extensions3D = []
        extensionsPR = []
        if file_exte_2d_param:
            extensions2D = eval(file_exte_2d_param)
        if file_exte_3d_param:
            extensions3D = eval(file_exte_3d_param)
        if file_exte_pr_param:
            extensionsPR = eval(file_exte_pr_param)
        for docBrws in self:
            try:
                fileExtension = docBrws.getFileExtension(docBrws)
                fileExtension = fileExtension.upper()
                if fileExtension in [x.upper() for x in extensions2D]:
                    docBrws.document_type = '2d'
                elif fileExtension in [x.upper() for x in extensions3D]:
                    docBrws.document_type = '3d'
                elif fileExtension in [x.upper() for x in extensionsPR]:
                    docBrws.document_type = 'pr'
                else:
                    docBrws.document_type = 'other'
            except Exception as ex:
                logging.error('Unable to compute document type for document %r, error %r' % (docBrws.id, ex))

    def _get_n_rel_doc(self):
        ir_attachment_relation = self.env['ir.attachment.relation']
        for ir_attachment_id in self:
            ir_a_id = ir_attachment_id.id
            ir_attachment_id.document_rel_count = ir_attachment_relation.search_count(['|',
                                                                                       ('parent_id', '=', ir_a_id),
                                                                                       ('child_id', '=', ir_a_id)])

    def _compute_linkedcomponents(self):
        for record in self:
            if record.linkedcomponents:
                record['is_linkedcomponents'] = True
            else:
                record['is_linkedcomponents'] = False
        return True

    def basePreview64ImgUrl(self):
        return "url(%s)" % self.basePreview64Img()

    def basePreview64Img(self):
        """
        Return the base64 image useful for html embedded content
        """
        if self.preview:
            return 'data:image/png;base64,%s' % self.preview.decode()
        return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAANkAAADoCAMAAABVRrFMAAAAeFBMVEX///8AAABERES0tLShoaFRUVFpaWnMzMzz8/P39/f8/Pzo6Oi4uLiwsLDCwsLj4+OPj4/X19fe3t7R0dFxcXGWlpY1NTVkZGRfX18TExOBgYGpqaklJSVTU1M8PDxzc3MwMDBJSUkrKyseHh6SkpKFhYUQEBAaGhrisuf5AAAKmklEQVR4nO2da3vyIAyG1enUOo+bh6mbh53+/z9837lZCSQhtFDorj5fJ47b0hCSAK1WrkX36fjZrqE+V4fdtEXqYR+7g+W0muBc01XsnpXXaYSATWL3yo/65kiM3SVf0kdkP3aH/GkOwAaxu+NTQ5XsJXZvfGqtgD3G7oxfLf7oI2u37//mW/at/E37I1PZTbnln8XuiW+9X8meYvfEt/IXrRe7J761uZJ1YvfEt3ok2ev4rj56WMrJ9oa/nLamYrJuzG4W0frPkt03ZA1ZMmrIGrJ01JA1ZOmoIWvI0lFDlgrZcP7Yf5xngk/WiWwxy4Mz+/sulhVTVR+y3avWow6RzfxVXcju2ojOj0yLepANqCTDgW5TCzImRflGvm51IENHYq4F0aoGZDsWjERLn8yeFMIHZPJkIytY+4w2TJ7sbCdrb7GGqZOZ8XlMc6Rl4mTCnPIr0jRxMmnmFXFGEicTgrVfzKZpk8nLAAZG27TJDmKyB6Nt2mQSk/8j0/AnTeZQbdMxGidNNpeTtY3GSZO5VI4O9cZ/hsxwi5MmGzuQGeXrSZP93Wf2d98zF9toBFeTJnOYz0xvP2my1puYzAzPpU0mL7K8M9qmTSY3IXXz9f/u+qz1ISQz9/SkTia0jiukaeJkwkAIlpNJnUxk+J+whsmTLexgX2jD5MksmZhv4btU0yezhomxAHGrFmStLgtGZXTrQMa6IuSG6VqQtaZHgmtNV4bUg4x42c6I65GrLmStgTFnr3Zsg9qQ/Vd/e9uR35tRmfer6kT2X8NRfzLpL0aCwquakTmoIWvI0lFD1pClo4asIUtHDVlDRmlkBt4DqxKy7LK2Otj2DvhVFWSj66l0ZioooCogU2KhZnVUOIUnA0FeIjYYQsHJtCx6dYYkNJl+atZessHKiwKTmfs+kOxkGIUlw2pK0RL0AApKhket+TChN4UkowrCuMiuTZn4PQ1IRu/UKeqMZMtzu/0s9GXCkTFpr2ej/Euk3JcRTfjByNjUObYnwqrsK28vcdNCkW05MPXMQbnU34rfvHpRIDJrof27/Tt0gfZ2KxSGTFAJJvjVobQiA25bbjiyjR3M3TnWZ31b+xBkIjBn59iwtcyR3oHITjIwYhMjKXOE8/Oad7JMfjzixv5tipCT1dmn7psso6oAMLk4xxnS/pND80w2lO8++paDc2ycWvitN8aZ8Us2+Gq7Se4c45vsVhXVg+SOnVxi55goUaL9NJ9kgk3dhr6kzjE1+feoBh7JBJWIiMwtcbhIk0uh+SNz2eqhCi0oNYSZxl+t8RbeyIof7b6UkHEjHV84+CIrc3+CZCHJ7j8OeW5BufPPBc4xX705C0ZW9ioPu3NsWfAhI9oLmcuuRVRHK5l+JJQus3s+yPiRIpLVObZ+g+GoeSCTHeFh0QcPJnAC9KhPeTJPVwyMWTKJ6dXiD6XJpLuNrGKdY9v5Scg3lCWzRN9cxDnHsn8Doj4lyXzeCcE5xyfZV6i1xeXI9JPey+lEkz0Lv0KJ+pQi831ZDukcy7cf34Z0GbJTSRBTlJly8Epzd6Y4mUOQSi4icuzg5Hxd0QqTZWHu6cP3F7hY4GuOvyiZY5BKLtQ5dnqhj1kZsoF8372jjhiZvdmXElx6LUFWJJYjFeIcD6nPdg7Lh/ntKQ+nj+P3zdtP/KAQWUgwzDlGQyybLnUs8WhUlKxYkEouwzk2TeOTPf2mWx0BWWgwM+unLSdeJqLSiSlsZier4v5BzTkGpvFgyZupmihLcStZJZd8vsGHoiSYlo4FF/2cw0ZW0SV9IPB78xoPBYoI+2cRWWX3zaqnz1xf7J5tAyShnYCsdJBKLsUW//6cxauQB/c2Mg9BKrludv1i4zbFKppuPw5HVimYsor8Xt+WLR0cvOZJH5Os8nswr+birf1c8A1Tlf82Otmu+gs+r2fQtE/2mdmhPFknc81A+9Ba+7VNDR7vZvery8Ljc//fP54IrrgIsWJ2FpZjuan/gS0Se13L0E2CjLH0C2advepyM3oaZFRJ3Bip6AF6oWvpEiFDL6roSqozTlQ4PQ0yLLgq9vA6+KogDTLT0o1ODs3R3FUSZGYSQ5SUUYTYyRTIjJBA5h5vN8POCZAZ1mNks4iYjFhYfLI3vUsFq4Q6WWpkepVI4eX8eZAWmW7XSsQpngdJkWljiBmKr/eH7Wx7YErOzymRaQ4+Wmz7X5uxMh1nj13CeHbSIdNK3vEiwJeJGUIY7NAabaWeLjKZNpVhj2JDFSP0sb7fQupxyY6wr2gE5pMus8Bcy3zUxiWDJY9UJoFZhZm1dfskyD5hN6m+7JlInXkI6dLybZUIOnt0/BY7h/gqc5oYJUAGngWZ8WyzxTHmRLGOTwadWDYcyBVGGmiL6GTAfnCPrM3ee2kMyE10MjAYbTF3bkOUvk6dRiaDWwusH+fq/bU0/CEyGcjAay4+tvZkYsj6UM7ikoGQk1ZoaB4E22a3MozNT0YkY370GV65z1TqQv/4JSoZ2OaiuRLIu3MRvUtDcyEHMcnAawPLeX/W2ZjjT5dSwCTSJCYZ+P1h5dpv/7ENF6R3DLcTfMQkU/sI3YirL5Uh2aVPyjuGRWKrmGRqAAS+JbmjPEBSFkcqJwhJhvHIwJ5UaONv4xSr1qP2Vb6DTy3ikQEPBBoQ5Q/YYpTwjmE91SQeGYgzApcDLFmwKB2+4xM+3248MuAGgr9A31d+lpb2kSTIYDBOS6tgl5KgR8WAKvVDPDK1/3BvhZ6Ox9Y3mHcMZvZ1PDLV04eviJFOe0eaI9UIwAz10iCDE7VZO4xVTlg+1YlHpo4nyzMTesdgdRDxmcnfs29h3rGemwZLvHXrFK7vvMS28UfYE9DC4sCBPkgPQPIvYLjBX9DZCtt5BDOBcFve1ucGTjeBhSfwQXDHEIvanVXvGA7prnPhhTeB/kMLgZKh3rHqVkM/bFLBTgpCoKQA+vpEeR+WD1XK4rv6dxSpvfAidQlJrM80Yd7xbVD39G+vuB76JvXJwJFGnmyDbfy42hv4ml2yNwE7zwpMW2gcxBSW5PwtaIUG47JGqmijiCFg3OHSk66+xQzez+CFb9WPHxPJ8B/VHmsxXrr+GTvx4s4cqL8znd8t7mKp3ddmKyY7QXjHMIKXn2Dt81gCuYDnq/lCTNId6+xce6VuGYAoBhIk+7SuEYdbYT/CRdo2A2U4jLB1QmDBO1W1P3IbPE+2b4YHI0xnlc/ZYIWlmwbuGBHb4ZGGEzOY9ysV6Lzu8XKVEkP+Ibgd8hle+nk45Ol/LdtxGxXeNSGSsUzhrAi3iT21R4b4F9xTYyo8q72vRiQjX7ZiOknu9xadOVixkOfAJN0Jf/e5uv46CHEKe/Rjw+/q9rChMoR6SFe3FNsjdtJSRbdnOAsvvtogDsnwAZ2u07OLV1Em7+lueosuDOc7IphY6BKGisScBLFff8yW7x9b2rcSnw0cRWWOTKj8Wjk34SZPogSnaKiCR5O8Jj0UfzSVHpynivMy01F2cgZL0adC5Ri++Ext4cJoaju/V1VVN5J5kthGFj3dJp4y0TnBnTKXkcXT2BbL2VjvAEpWC+a44DN71kQNNF+eEKz1OHmXQ6Lh/OH98LL6nsHfXjfb7sR+NNs/6gavFaGyHtoAAAAASUVORK5CYII='

    def _getHtmlDocument(self):
        view_obj = self.env['ir.ui.view']
        html_rendered = view_obj._render_template('plm.document_search_button', {'doc': self})
        html_tooltip = view_obj._render_template('plm.document_search_tooltip', {'doc': self})
        return html_rendered, html_tooltip

    @api.model
    def getHtmlDocument(self, attachment_id):
        return self.browse(attachment_id)._getHtmlDocument()

    has_error = fields.Boolean("Has Error",
                               compute='_checkSavingError',
                               store=True)

    #
    #
    #
    @api.depends("datas")
    def _checkSavingError(self):
        for ir_attachment_id in self:
            ir_attachment_id.has_error = not ir_attachment_id.is_last_save_ok()

    def getLastError(self):
        self.ensure_one()
        for ir_attachment_id in self:
            key = f"{ir_attachment_id.engineering_code}_{ir_attachment_id.engineering_revision}"
            for dbthread in self.env['plm.dbthread'].get_last_dbthread(key):
                if dbthread.done == True and dbthread.error_message:
                    return dbthread.error_message
        return ''

    def is_last_save_ok(self):
        """

        """
        for ir_attachment_id in self:
            key = f"{ir_attachment_id.engineering_code}_{ir_attachment_id.engineering_revision}"
            for dbthread in self.env['plm.dbthread'].get_last_dbthread(key):
                if dbthread.done == True and dbthread.error_message:
                    return False
        return True

    @api.model
    def getAttachedHtmlDoucment(self, product_ids):
        """
        render the html search view linked document
        :return: [(ir_attachment.id, <product.product>product_id.id, html_rendered, html_tooltip),..]
        """
        out = []

        for product_id in self.env['product.product'].browse(product_ids):
            for ir_attachment in product_id.linkeddocuments:
                html_rendered, html_tooltip = ir_attachment._getHtmlDocument()
                out.append((ir_attachment.id, product_id.id, html_rendered, html_tooltip))
        return out

    @api.model
    def getAttachedHtmlDoucmentTemplate(self, product_ids):
        """
        render the html search view linked document
        :return: [(ir_attachment.id, <product.template>product_id.id, html_rendered, html_tooltip),..]
        """
        product_product_id = self.env['product.product'].search([('product_tmpl_id', 'in', product_ids)])
        return self.getAttachedHtmlDoucment(product_product_id.ids)

    def _attachment_revision_count(self):
        """
        get All version product_tempate based on this one
        """
        for ir_attachment_id in self:
            if ir_attachment_id.engineering_code is not False:
                ir_attachment_id.attachment_revision_count = ir_attachment_id.search_count(
                    [('engineering_code', '=', ir_attachment_id.engineering_code)])
            else:
                ir_attachment_id.attachment_revision_count = 0

    @api.model
    def CheckedIn(self, files, default=None):
        """
            Get checked status for requested files
        """
        retValues = []

        def getcheckedfiles(files):
            res = []
            for fileName in files:
                plmDocList = self.search([('name', 'ilike', fileName)], order='engineering_revision DESC')
                if len(plmDocList) > 0:
                    ids = plmDocList.ids
                    ids.sort()
                    docBrws = self.browse(ids[len(ids) - 1])
                    checkoutFlag = docBrws._is_checkedout_for_me()
                    res.append([fileName, not checkoutFlag])
            return res

        if len(files) > 0:  # no files to process
            retValues = getcheckedfiles(files)
        return retValues

    @api.model
    def GetUpdated(self, vals):
        """
            Get Last/Requested revision of given items (by engineering_code, revision, update time)
        """
        docData, attribNames = vals
        ids = self.GetLatestIds(docData)
        return self.read(list(set(ids)), attribNames)

    @api.model
    def GetLatestIds(self, vals, forceCADProperties=False):
        """
            Get Last/Requested revision of given items (by engineering_code, revision, update time)
        """
        ids = []

        def getCompIds(docName, docRev):
            if docRev is None or docRev is False:
                docBrwsList = self.search([('engineering_code', '=', docName)], order='engineering_revision')
                if len(docBrwsList) > 0:
                    ids.append(docBrwsList.ids[-1])
            else:
                ids.extend(self.search([('engineering_code', '=', docName), ('engineering_revision', '=', docRev)]).ids)

        for docName, docRev, docIdToOpen in vals:
            docBrowse = self.browse(docIdToOpen)
            checkOutUser = docBrowse.get_checkout_user()
            if checkOutUser:
                isMyDocument = docBrowse.isCheckedOutByMe()
                if isMyDocument:
                    return []  # Document properties will be not updated
                else:
                    getCompIds(docName, docRev)
            else:
                getCompIds(docName, docRev)
        return list(set(ids))

    def isCheckedOutByMe(self):
        checkoutBrwsList = self.env['plm.checkout'].search(
            [('documentid', '=', self.id), ('userid', '=', self.env.uid)])
        for checkoutBrws in checkoutBrwsList:
            return checkoutBrws.id
        return False

    def checkoutByMeWithUser(self):
        isCheckedOutToMe = False
        checkOutUser = ''
        for objDoc in self:
            checkoutUserBrws = objDoc.get_checkout_user()
            if checkoutUserBrws:
                checkOutUser = checkoutUserBrws.name
                if checkoutUserBrws.id == self.env.user.id:
                    isCheckedOutToMe = True
                    break
        return isCheckedOutToMe, checkOutUser

    @api.model
    def CheckAllFiles(self, request, default=None):
        """
            Evaluate documents to return
        """
        forceFlag = False
        outIds = []
        doc_id, listedFiles, selection, hostname, hostpws = request
        docBrws = self.browse(doc_id)
        outIds.append(doc_id)
        if selection is False:
            selection = 1  # Case of selected
        if selection < 0:  # Case of force refresh PWS
            forceFlag = True
            selection = selection * (-1)
        if docBrws.is2D():
            outIds.extend(self.getRelatedLyTree(doc_id))
        outIds.extend(self.getRelatedHiTree(doc_id, recursion=True, getRftree=True))
        outIds = list(set(outIds))
        if selection == 2:  # Case of latest
            outIds = self._getlastrev(outIds)
        return self._data_check_files(outIds, listedFiles, forceFlag, False, hostname, hostpws)

    def is2D(self):
        self.ensure_one()
        for docBrws in self:
            if docBrws.document_type.upper() == '2D':
                return True
            break
        return False

    def is3D(self):
        self.ensure_one()
        for docBrws in self:
            if docBrws.document_type.upper() == '3D':
                return True
            break
        return False

    def isPresentation(self):
        self.ensure_one()
        for docBrws in self:
            if docBrws.document_type.upper() == 'PR':
                return True
            break
        return False

    @api.model
    def CheckInRecursive(self, request, default=None):
        """
            Evaluate documents to return
        """

        def getDocId(args):
            engineering_code = args.get('engineering_code')
            docRev = args.get('engineering_revision')
            for docBrwsList in self.search([('engineering_code', '=', engineering_code),
                                            ('engineering_revision', '=', docRev)]):
                return docBrwsList.id
            logging.warning(
                'Document with engineering_code "%s" and revision "%s" not found' % (engineering_code, docRev))
            return False

        oid, _listedFiles, selection = request
        oid = getDocId(oid)
        docBrws = self.browse(oid)
        if not docBrws.isCheckedOutByMe():
            logging.info(
                'Document %r is not in check out by user %r so cannot be checked-in recursively' % (oid, self.env.uid))
            return False
        if docBrws.file_size <= 0 or not docBrws.name:
            logging.warning('Document %r has not document content so cannot be checked-in recirsively' % (oid))
            return False
        if selection is False:
            selection = 1
        if selection < 0:
            selection = selection * (-1)
        docArray = self.getRelatedAllLevelDocumentsTree(docBrws)
        if selection == 2:
            docArray = self._getlastrev(docArray)
        checkoutObj = self.env['plm.checkout']
        msg = ''
        for x in docArray:
            if x.has_error:
                msg += x.engineering_code + "\n"
        if msg:
            raise UserError(msg)
        for docId in docArray:
            checkOutBrwsList = checkoutObj.search([('documentid', '=', docId), ('userid', '=', self.env.uid)])
            checkOutBrwsList.unlink()
        return self.browse(docArray).read(['name'])

    @api.model
    def GetSomeFiles(self,
                     request,
                     default=None):
        """
            Extract documents to be returned
        """
        forceFlag = False
        ids, listedFiles, selection = request
        if not selection:
            selection = 1

        if selection < 0:
            forceFlag = True
            selection = selection * (-1)

        if selection == 2:
            docArray = self._getlastrev(ids)
        else:
            docArray = ids
        return self.browse(docArray)._data_get_files(listedFiles, forceFlag)

    def action_view_rel_doc(self):
        action = self.env.ref('plm.act_view_doc_related').read()[0]
        action['domain'] = ['|', ('parent_id', 'in', self.ids),
                            ('child_id', 'in', self.ids)]
        return action

    def GetRelatedDocs(self, default=None, getBrowse=False):
        """
            Extract documents related to current one(s) (layouts, referred models, etc.)
        """
        related_documents = []
        read_docs = []
        for oid in self.ids:
            read_docs.extend(self.getRelatedRfTree(oid, recursion=False))
            read_docs.extend(self.getRelatedLyTree(oid))
            read_docs.extend(self.getRelatedPrTree(oid))

            # for rfModel in rfTree:
            #    read_docs.extend(self.getRelatedLyTree(rfModel))
        read_docs = list(set(read_docs))
        for document in self.browse(read_docs).sorted('document_type', reverse=True):  # 3d before 2d
            if getBrowse:
                related_documents.append(document)
            else:
                related_documents.append([document.id,
                                          document.engineering_code,
                                          '' if document.preview is None else document.preview,
                                          document.engineering_revision,
                                          document.description])
        return related_documents

    @api.model
    def GetRelatedDocsByAttrs(self, docPropsList=[]):
        """
            Extract documents related to current one(s) (layouts, referred models, etc.)
        """
        if not docPropsList:
            return False
        docProps = docPropsList[0]
        docRev = docProps.get('engineering_revision', None)
        if docRev is None:
            logging.warning(
                'Current document has not engineering_revision attribute %r.\n Cannot get related documents.' % (
                    docProps))
            return False
        docName = docProps.get('engineering_code', '')
        documentBrws = self.search([('engineering_code', '=', docName),
                                    ('engineering_revision', '=', docRev)])
        if not documentBrws:
            logging.warning(
                'Unbale to find document %r with revision %r.\n Cannot get related documents.' % (docName, docRev))
            return False
        return documentBrws.GetRelatedDocs(documentBrws.ids)

    @api.model
    def getServerTime(self, _unusedVal=False):
        """
            calculate the server db time
        """
        return datetime.now()

    @api.model
    def getLastTime(self, oid, default=None):
        """
            get document last modification time
        """
        obj = self.browse(oid)
        if (obj.write_date is not False):
            return obj.write_date
        else:
            return obj.create_date

    @api.model
    def getUserSign(self, userId):
        """
            get the user name
        """
        userType = self.env['res.users']
        uiUser = userType.browse(userId)
        return uiUser.name

    def _getbyrevision(self, engineering_code, revision):
        result = False
        for result in self.search([('engineering_code', '=', engineering_code),
                                   ('engineering_revision', '=', revision)]):
            return result
        return result

    @api.model
    def getCheckedOut(self, oid, default=None):
        checkoutType = self.env['plm.checkout']
        checkoutBrwsList = checkoutType.search([('documentid', '=', oid)])
        for checkOutBrws in checkoutBrwsList:
            return (checkOutBrws.documentid.engineering_code,
                    checkOutBrws.documentid.engineering_revision,
                    self.getUserSign(checkOutBrws.userid.id),
                    checkOutBrws.hostname)
        return ('', False, '', '')

    def _getCheckOutUser(self):
        for ir_attachment_id in self:
            checkoutType = self.env['plm.checkout']
            checkoutBrwsList = checkoutType.search([('documentid', '=', ir_attachment_id.id)])
            for checkOutBrws in checkoutBrwsList:
                return checkOutBrws.userid
        return self.env['res.users']

    @api.model
    def _file_delete(self, fname):
        """
            Delete file only if is not saved on plm.backupdoc
        """
        backupDocBrwsList = self.env['plm.backupdoc'].search([('existingfile', '=', fname)])
        if not backupDocBrwsList:
            return super(IrAttachment, self)._file_delete(fname)

    @api.model
    def GetNextDocumentName(self, documentName):
        """
            Return a new name due to sequence next number.
            
            NEW client set in the contex this informations
            {
            #
            #
            #
            'document_attrs': {} # dictionary like of attribute changed for products
            'product_attrs': {} # dictionary like of attribute changed for documents
            'ori_document_attrs': {} # dictionary like of attribute from cad application for products
            'orig_product_attrs': {} # dictionary like of attribute from cad application for documents
            'mode':'ir.attachment' or 'product.product' 
            #
            # those other value are for compatibylity with the old version
            #
            'active_file_doc_attrs': {}, 
            'all_attributes': {'product': self.attributes,
                                'document':self._documentAttrs
            },
            #
            'mode':'ir.attachment'
        """
        ctx = self.env.context
        eng_code = ctx.get('product_attrs', {}).get("engineering_code") or ctx.get('engineering_code', '')
        #
        # this check is to solve some issiued on the client call
        #
        if isinstance(documentName, list):
            documentName = documentName[0]
        #
        if eng_code:
            documentName = eng_code
        nextDocNum = self.env['ir.sequence'].next_by_code('ir.attachment.progress')
        return documentName + '-' + nextDocNum

    @api.model
    def canBeSavedClient(self, documentValues={}, returnCode=False):
        engineering_code = documentValues.get('engineering_code')
        docRev = documentValues.get('engineering_revision')
        for docBrws in self.search([('engineering_code', '=', engineering_code),
                                    ('engineering_revision', '=', docRev)
                                    ]):
            return docBrws.canBeSaved(False, returnCode=returnCode)
        if returnCode:
            return True, _('Document %r with revision %r not present in Odoo.') % (engineering_code, docRev), 'NO_ERROR'
        return True, _('Document %r with revision %r not present in Odoo.') % (engineering_code, docRev)

    @api.model
    def canBeSaved(self, raiseError=False, returnCode=False, skipCheckOutControl=False):
        """
        check if the document can be saved and raise exception in case is not possible
        """
        outMessage = ''
        outCode = 'NO_ERROR'
        if self.engineering_state in [RELEASED_STATUS, OBSOLATED_STATUS]:
            outMessage = _("Document is released and cannot be saved")
            outCode = 'DOC_RELEASED'
            if raiseError:
                raise UserError(outMessage)
        if not skipCheckOutControl:
            checkOutObject = self.getCheckOutObject()
            if checkOutObject:
                if checkOutObject.userid.id != self.env.uid:
                    outMessage = _("Document is Check-Out from User %r", checkOutObject.name)
                    outCode = 'DOC_CHECKOUT_FROM_USER'
                    if raiseError:
                        raise UserError(outMessage)
            else:
                outMessage = _("Document in check-In unable to save!")
                outCode = 'DOC_CHECKIN'
                if raiseError:
                    raise UserError(outMessage)

        def returnTuple():
            if len(outMessage) > 0:
                return False, outMessage
            return True, ''

        if returnCode:
            return returnTuple() + (outCode,)
        return returnTuple()

    @api.model
    def getCheckOutObject(self):
        checkoutIDs = self.env['plm.checkout'].search([('documentid', '=', self.id)])
        for checkoutID in checkoutIDs:
            return checkoutID
        return None

    @api.model
    def saveStructure(self, arguments):
        """
        save the structure passed
        self['FILE_PATH'] = ''
        self['PDF_PATH'] = ''
        self['PRODUCT_ATTRIBUTES'] = []
        self['DOCUMENT_ATTRIBUTES'] = []
        self['RELATION_ATTRIBUTES'] = []
        self['RELATIONS'] = [] # tutte le relazioni vanno qui ma devo metterci un attributo che mi identifica il tipo
                                # 2d2d 3d3d 3d2d o niente
        self['DOCUMENT_DATE'] = None
        """
        start = time.time()
        if len(arguments) == 3:
            cPickleStructure, hostName, hostPws = arguments
            skipDocumentCheckOnBom = False
        else:
            cPickleStructure, hostName, hostPws, skipDocumentCheckOnBom = arguments
        documentAttributes = {}
        documentRelations = {}
        productAttributes = {}
        productRelations = {}
        productDocumentRelations = {}
        objStructure = json.loads(cPickleStructure)

        documentAttribute = objStructure.get('DOCUMENT_ATTRIBUTES', {})
        if documentAttribute:
            for brwItem in self.search([('engineering_code', '=', documentAttribute.get('engineering_code', '')),
                                        ('engineering_revision', '=',
                                         documentAttribute.get('engineering_revision', -1))]):
                brwItem.canBeSaved(raiseError=True)

        def populateStructure(parentItem=False, structure={}, parentCreateBOM=True):
            documentId = False
            productId = False
            createBom = structure.get('CREATE_BOM', True)
            documentProperty = structure.get('DOCUMENT_ATTRIBUTES', False)
            docType = structure.get('DOC_TYPE', '')
            if documentProperty and structure.get('FILE_PATH', False):
                documentId = id(documentProperty)
                documentAttributes[documentId] = documentProperty
            productProperty = structure.get('PRODUCT_ATTRIBUTES', False)
            if productProperty and productProperty.get('engineering_code', ''):
                productId = id(productProperty)
                productAttributes[productId] = productProperty
            if productId and documentId:
                listRelated = productDocumentRelations.get(productId, [])
                listRelated.append(documentId)
                productDocumentRelations[productId] = listRelated
            if parentItem and productId and docType != '2D':
                # I'm a 3D file
                parentDocumentId, parentProductId = parentItem
                relationAttributes = structure.get('MRP_ATTRIBUTES', {})
                forceQty = structure.get('FORCE_QTY', 1)
                if forceQty:
                    relationAttributes['product_qty'] = forceQty
                childRelations = documentRelations.get(parentDocumentId, [])
                childRelations.append((documentId, relationAttributes.get('TYPE', '')))
                if parentDocumentId:
                    documentRelations[parentDocumentId] = list(set(childRelations))
                if parentProductId and parentCreateBOM:  # Case of part - assembly
                    if not documentId:
                        documentId = parentDocumentId
                    itemTuple = (productId, documentId, relationAttributes)
                    listItem = productRelations.get(parentProductId, [])
                    listItem.append(itemTuple)
                    productRelations[parentProductId] = listItem
                else:
                    if productId and parentDocumentId:
                        if not parentProductId:  # Case of drawing - model relation
                            listRelated = productDocumentRelations.get(productId, [])
                            listRelated.append(parentDocumentId)
                            productDocumentRelations[productId] = listRelated
            for subStructure in structure.get('RELATIONS', []):
                populateStructure((documentId, productId), subStructure, createBom)

        populateStructure(structure=objStructure)

        # Save the document
        logging.info("Saving Document")
        alreadyEvaluated = []
        for documentAttribute in list(documentAttributes.values()):
            try:
                documentAttribute['TO_UPDATE'] = False
                skipCheckOut = documentAttribute.get('SKIP_CHECKOUT', False)
                docBrws = False
                for brwItem in self.search([('engineering_code', '=', documentAttribute.get('engineering_code')),
                                            ('engineering_revision', '=',
                                             documentAttribute.get('engineering_revision'))]):
                    if brwItem.id in alreadyEvaluated:
                        docBrws = brwItem  # To skip creation
                        documentAttribute[
                            'TO_UPDATE'] = False  # To skip same document preview/pdf uploading by the client
                        break
                    if brwItem.engineering_state not in [RELEASED_STATUS, OBSOLATED_STATUS]:
                        if brwItem.needUpdate():
                            brwItem.write(documentAttribute)
                            documentAttribute['TO_UPDATE'] = True
                    docBrws = brwItem
                    alreadyEvaluated.append(docBrws.id)
                if not docBrws:
                    docBrws = self.create(documentAttribute)
                    alreadyEvaluated.append(docBrws.id)
                    if not skipCheckOut:
                        docBrws.checkout(hostName, hostPws)
                    documentAttribute['TO_UPDATE'] = True
                elif skipCheckOut:
                    if docBrws.isCheckedOutByMe():
                        docBrws._check_in()
                documentAttribute['id'] = docBrws.id
            except Exception as ex:
                logging.error(ex)
                raise ex

        # Save the product
        # Save product - document relation
        logging.info("Saving Product")
        productsEvaluated = []
        productTemplate = self.env['product.product']
        for refId, productAttribute in list(productAttributes.items()):
            try:
                linkedDocuments = set()
                for refDocId in productDocumentRelations.get(refId, []):
                    linkedDocuments.add((4, documentAttributes[refDocId].get('id', 0)))
                prodBrws = False
                for brwItem in productTemplate.search(
                    [('engineering_code', '=', productAttribute.get('engineering_code')),
                     ('engineering_revision', '=', productAttribute.get('engineering_revision'))]):
                    if brwItem.id in productsEvaluated:
                        prodBrws = brwItem
                        break
                    if brwItem.engineering_state not in [RELEASED_STATUS, OBSOLATED_STATUS]:
                        brwItem.write(productAttribute)
                    prodBrws = brwItem
                    productsEvaluated.append(brwItem.id)
                    break
                if not prodBrws:
                    if not productAttribute.get('name', False):
                        productAttribute['name'] = productAttribute.get('engineering_code', False)
                    if not productAttribute.get('engineering_code',
                                                False):  # I could have a document without component, so not create product
                        continue
                    prodBrws = productTemplate.create(productAttribute)
                    productsEvaluated.append(prodBrws.id)
                if linkedDocuments:
                    prodBrws.write({'linkeddocuments': list(linkedDocuments)})
                productAttribute['id'] = prodBrws.id
            except Exception as ex:
                logging.error(ex)
                raise ex

        # Save the document relation
        logging.info("Saving Document Relations")
        documentRelationTemplate = self.env['ir.attachment.relation']
        createdDocRels = []
        for parentId, childrenRelations in list(documentRelations.items()):
            try:
                trueParentId = documentAttributes[parentId].get('id', 0)
                for objBrw in documentRelationTemplate.search([('parent_id', '=', trueParentId)]):
                    found = False
                    for childId, relationType in childrenRelations:
                        trueChildId = documentAttributes.get(childId, {}).get('id', 0)
                        if objBrw.parent_id.id == trueParentId and objBrw.child_id.id == trueChildId and objBrw.link_kind == relationType:
                            found = True
                            key = '%s_%s_%s' % (trueParentId, trueChildId, relationType)
                            if key in createdDocRels:
                                continue
                            createdDocRels.append(key)
                            break
                    if not found:  # Line removed from previous save
                        objBrw.unlink()
                for childId, relationType in childrenRelations:
                    trueChildId = documentAttributes.get(childId, {}).get('id', 0)
                    key = '%s_%s_%s' % (trueParentId, trueChildId, relationType)
                    if key in createdDocRels:
                        continue
                    createdDocRels.append(key)
                    documentRelationTemplate.create({'parent_id': trueParentId,
                                                     'child_id': trueChildId,
                                                     'link_kind': relationType})
            except Exception as ex:
                logging.error(ex)
                raise ex
        # Save the product relation
        domain = [('engineering_state', 'in', ['installed', 'to upgrade', 'to remove']),
                  ('name', '=', 'plm_engineering')]
        apps = self.env['ir.module.module'].sudo().search_read(domain, ['name'])
        bomType = 'normal'
        if apps:
            bomType = 'ebom'
        logging.info("Saving Product Relations")
        mrpBomTemplate = self.env['mrp.bom']
        for parentId, childRelations in list(productRelations.items()):
            try:
                trueParentId = productAttributes[parentId].get('id')
                brwProduct = productTemplate.search([('id', '=', trueParentId)])
                productTempId = brwProduct.product_tmpl_id.id
                brwBoml = mrpBomTemplate.search([('product_tmpl_id', '=', productTempId)])
                if not brwBoml:
                    brwBoml = mrpBomTemplate.create({'product_tmpl_id': productTempId,
                                                     'type': bomType})
                # delete rows
                if skipDocumentCheckOnBom:
                    for brwBom in brwBoml:
                        # If not source document I need to clean all bom lines losting also custom lines...
                        brwBom.bom_line_ids.unlink()
                else:
                    for _, documentId, _ in childRelations:
                        trueDocumentId = documentAttributes.get(documentId, {}).get('id', 0)
                        if trueDocumentId:  # seems strange this .. but i will delete only the bom with the right source id
                            for brwBom in brwBoml:
                                brwBom.delete_child_row(trueDocumentId)
                            break
                # add rows
                for childId, documentId, relationAttributes in childRelations:
                    if skipDocumentCheckOnBom:
                        if not childId:
                            logging.warning("Bad relation request %r, %r" % (childId, documentId))
                            continue
                    elif not (childId and documentId):
                        logging.warning("Bad relation request %r, %r" % (childId, documentId))
                        continue
                    trueChildId = productAttributes[childId].get('id')
                    trueDocumentId = documentAttributes.get(documentId, {}).get('id')
                    brwBoml.add_child_row(trueChildId, trueDocumentId, relationAttributes, bomType)
            except Exception as ex:
                logging.error(ex)
                raise ex
        jsonify = json.dumps(objStructure)
        end = time.time()
        logging.info("Time Spend For save structure is: %s" % (str(end - start)))
        return jsonify

    def checkout(self, hostName, hostPws, showError=True, user_id=False):
        """
        check out the current document
        """
        if not user_id:
            user_id = self.env.uid
        plm_checkout_id = False
        msg = ''
        for document in self:
            checkout_id = document.isCheckedOutByMe()
            if checkout_id:
                plm_checkout_id = checkout_id
            else:
                res, msg = document.canCheckOut(showError=showError)
                if res:
                    values = {'userid': user_id,
                              'hostname': hostName,
                              'hostpws': hostPws,
                              'documentid': document.id}
                    plm_checkout_id = self.env['plm.checkout'].create(values).id
                    break
        return plm_checkout_id, msg

    @api.model
    def clientCanCheckOut(self, doc_attrs):
        for attachment_id in self.getDocumentBrws(doc_attrs):
            return attachment_id.canCheckOut1()
        return False, 'not_found', f'File Not found from attributes {doc_attrs}'

    def canCheckOut1(self):
        for docBrws in self:
            if docBrws.isCheckedOutByMe():
                msg = _(f"Unable to check-Out a document that is already checked Out By {docBrws.checkout_user}")
                return docBrws.id, 'check_out_by_me', msg
            if docBrws.is_checkout:
                msg = _(f"Unable to check-Out a document that is already checked IN by user {docBrws.checkout_user}")
                return docBrws.id, 'check_out_by_user', msg
            if docBrws.engineering_state not in [START_STATUS, False]:
                msg = _(f"Unable to check-Out a document that is in state {docBrws.engineering_state}")
                return docBrws.id, 'check_out_released', msg
            return docBrws.id, 'check_in', ''
        raise Exception()

    def canCheckOut(self, showError=False):
        for docBrws in self:
            if docBrws.is_checkout:
                msg = _("Unable to check-Out a document that is already checked IN by user %r" % docBrws.checkout_user)
                if showError:
                    raise UserError(msg)
                return False, msg
            if docBrws.engineering_state not in [START_STATUS, False]:
                msg = _("Unable to check-Out a document that is in state %r" % docBrws.engineering_state)
                if showError:
                    raise UserError(msg)
                return False, msg
            return True, ''
        return False, 'No document provided'

    @api.model
    def needUpdate(self):
        """
        check if the file need to be updated
        """
        checkoutIds = self.env['plm.checkout'].search([('documentid', '=', self.id),
                                                       ('userid', '=', self.env.uid)])
        for _brw in checkoutIds:
            return True
        return False

    def getDocumentInfos(self):
        """
            Document infos for clone/revision procedure
        """
        return {'engineering_code': self.engineering_code or '',
                'engineering_revision': self.engineering_revision,
                'description': self.description or '',
                'desc_modify': self.desc_modify or '',
                'doc_type': self.document_type,
                '_id': self.id,
                'can_revise': self.canBeRevised(),
                'DOC_TYPE': self.document_type
                }

    @api.model
    def getCloneRevisionStructure(self, values=[]):
        if not values:
            return {}
        docProps = values[0]
        engineering_code = docProps.get('engineering_code', '')
        docRev = docProps.get('engineering_revision', None)
        if not engineering_code or docRev is None:
            logging.warning('No name or not revision passed by the client %r' % (docProps))
            return {}
        docBrws = self.search([('engineering_code', '=', engineering_code),
                               ('engineering_revision', '=', docRev)])

        rootDocInfos = docBrws.getDocumentInfos()
        rootDocInfos['root_document'] = True
        linkedDocs = [{'component': {}, 'document': rootDocInfos}]
        linkedDocs.extend(docBrws.computeLikedDocuments())
        return {'root_props': docBrws.getDocumentInfos(),
                'documents': linkedDocs,
                'bom': []}

    def computeLikedDocuments(self):
        """
            Get child documents in document relations
        """
        # Check dei grezzi e delle relazioni parte modello. Non devono comparire nella vista
        docList = []
        linkedDocEnv = self.env['ir.attachment.relation']
        for linkedBrws in linkedDocEnv.search([('child_id', '=', self.id)]):
            if linkedBrws.parent_id.document_type.upper() == '2D':  # Append only 2D relations
                docList.append({'component': {}, 'document': linkedBrws.parent_id.getDocumentInfos()})
        return docList

    def canBeRevised(self):
        for docBrws in self:
            if docBrws.engineering_state == RELEASED_STATUS and docBrws.ischecked_in():
                return True
        return False

    def cleanDocumentRelations(self):
        linkedDocEnv = self.env['ir.attachment.relation']
        for docBrws in self:
            for linkedBrws in linkedDocEnv.search([('child_id', '=', docBrws.id), ('parent_id', '=', docBrws.id)]):
                linkedBrws.unlink()

    @api.model
    def getIdFromAttrs(self, attrs):
        for ir_attachment in self.getDocumentBrws(json.loads(attrs)):
            return ir_attachment.id
        return False

    def getDocumentBrws(self, docVals):
        """
        function to convert dict client info into attachment browse record
        :docVals could be dictionaty or list of dictionaty
                    es1. {'engineering_code': '102030', 'engineering_revision': 0}
                    es2. [{'engineering_code': '102030', 'engineering_revision': 0},{ },..]
        :return: browse_record(ir_attachment)
        """
        if not isinstance(docVals, list):
            docVals = [docVals]
        out = self.env[self._name]
        for doc_dict in docVals:
            docName = doc_dict.get('engineering_code', '')
            docRev = doc_dict.get('engineering_revision', None)
            if not docName or docRev is None:
                continue
            for ir_attachment_id in self.search([('engineering_code', '=', docName),
                                                 ('engineering_revision', '=', docRev)]):
                out += ir_attachment_id
                break
        return out

    def checkStructureDocument(self, docAttrs):
        docName = docAttrs.get('engineering_code', '')
        docRev = int(docAttrs.get('engineering_revision', 0) or 0)
        docAttrs['engineering_revision'] = docRev
        docBrwsList = self.search([('engineering_code', '=', docName)], order='engineering_revision DESC')
        existingDocs = {}
        graterDocBrws = None
        matchDocBrws = None
        docAttrs['engineering_state'] = START_STATUS
        for docBrws in docBrwsList:
            if docBrws.engineering_revision == docRev:
                docAttrs['engineering_state'] = docBrws.engineering_state
                matchDocBrws = docBrws
            if not graterDocBrws:
                graterDocBrws = docBrws
            existingDocs[docBrws.engineering_revision] = (docBrws.engineering_code, docBrws.engineering_state)
        docAttrs['existing_docs'] = existingDocs
        docAttrs['is_latest_revision'] = False
        if graterDocBrws and (graterDocBrws == matchDocBrws):
            docAttrs['is_latest_revision'] = True
            if graterDocBrws:
                docAttrs['can_be_revised'] = graterDocBrws.canBeRevised()
        if not matchDocBrws:  # CAD document revision is grater than Odoo one
            if graterDocBrws:
                docAttrs['can_be_revised'] = graterDocBrws.canBeRevised()
        return docAttrs

    def checkStructureComponent(self, compAttrs):
        prodProd = self.env['product.product']
        engCode = compAttrs.get('engineering_code', '')
        engRev = int(compAttrs.get('engineering_revision', 0) or 0)
        compAttrs['engineering_revision'] = engRev
        prodBrwsList = prodProd.search([('engineering_code', '=', engCode)], order='engineering_revision DESC')
        existingCompRevisions = {}
        foundCompBrws = None
        graterCompBrws = None
        compAttrs['engineering_state'] = START_STATUS
        for compBrws in prodBrwsList:
            if engRev == compBrws.engineering_revision:
                compAttrs['engineering_state'] = compBrws.engineering_state
                foundCompBrws = compBrws
            if not graterCompBrws:
                graterCompBrws = compBrws
            existingCompRevisions[compBrws.engineering_revision] = (
            compBrws.engineering_code, compBrws.engineering_state)
        compAttrs['existing_comps'] = existingCompRevisions
        if graterCompBrws == foundCompBrws:
            compAttrs['is_latest_revision'] = True
            if graterCompBrws:
                compAttrs['can_be_revised'] = graterCompBrws.canBeRevised()
        if not foundCompBrws:
            if graterCompBrws:
                compAttrs['can_be_revised'] = graterCompBrws.canBeRevised()
        return compAttrs

    @api.model
    def checkSyncImportStructure(self, args):
        def recursion(parentNode):
            docAttrs = parentNode.get('DOCUMENT_ATTRIBUTES', {})
            compAttrs = parentNode.get('PRODUCT_ATTRIBUTES', {})
            parentNode['DOCUMENT_ATTRIBUTES'] = self.checkStructureDocument(docAttrs)
            parentNode['PRODUCT_ATTRIBUTES'] = self.checkStructureComponent(compAttrs)
            childrenNodes = parentNode.get('RELATIONS', {})
            for node in childrenNodes:
                index = childrenNodes.index(node)
                updatedNode = recursion(node)
                parentNode['RELATIONS'][index] = updatedNode
            return parentNode

        jsonNode = args[0]
        rootNode = json.loads(jsonNode)
        rootNode = recursion(rootNode)
        return json.dumps(rootNode)

    @api.model
    def checkStructureExistance(self, args):
        prodProdEnv = self.env['product.product']
        jsonNode = args[0]
        rootNode = json.loads(jsonNode)

        def getLinkedDocumentsByComponent(node, compBrws):
            """
                Append in the node relations documents taken by linkeddocuments
            """
            if compBrws.id:
                # In this case I start to clone a part/assembly which has a related drawing,
                # I don't have in the CAD structure the link between them...
                for docBrws in compBrws.linkeddocuments:
                    if docBrws.id == node['DOCUMENT_ATTRIBUTES'].get('_id'):
                        # I'm evaluating root part/document
                        continue
                    newNode = copy.deepcopy(node)
                    newNode['DOCUMENT_ATTRIBUTES'] = docBrws.getDocumentInfos()
                    newNode['DOCUMENT_ATTRIBUTES']['CAN_BE_REVISED'] = docBrws.canBeRevised()
                    node['RELATIONS'].append(newNode)

        def getLinkedDocumentsByDocument(node, docBrws):
            """
                Append in the node relations documents taken by ir.attachment.relation
            """
            linkedDocEnv = self.env['ir.attachment.relation']
            if docBrws.id:
                typeDoc = ''
                if docBrws.document_type.upper() == '3D':
                    typeDoc = 'child_id'
                else:
                    typeDoc = 'parent_id'
                for docLinkBrws in linkedDocEnv.search([(typeDoc, '=', docBrws.id)]):
                    relatedDocBrws = False
                    if docLinkBrws.child_id.id == docBrws.id:
                        relatedDocBrws = docLinkBrws.parent_id
                    else:
                        relatedDocBrws = docLinkBrws.child_id
                    if relatedDocBrws and relatedDocBrws.document_type.upper() == '2D':  # If not 2D is a raw part
                        newNode = copy.deepcopy(node)
                        newNode['DOCUMENT_ATTRIBUTES'] = relatedDocBrws.getDocumentInfos()
                        newNode['DOCUMENT_ATTRIBUTES']['CAN_BE_REVISED'] = relatedDocBrws.canBeRevised()
                        node['RELATIONS'].append(newNode)

        def recursionUpdate(node, isRoot=False):
            # Update root component and document ids
            compVals = node.get('PRODUCT_ATTRIBUTES', {})
            compBrws = prodProdEnv.getComponentBrws(compVals)
            node['PRODUCT_ATTRIBUTES'] = compBrws.getComponentInfos()
            node['PRODUCT_ATTRIBUTES']['CAN_BE_REVISED'] = compBrws.canBeRevised()
            rootDocVals = node.get('DOCUMENT_ATTRIBUTES', {})
            rootDocBrws = self.getDocumentBrws(rootDocVals)
            node['DOCUMENT_ATTRIBUTES'] = rootDocBrws.getDocumentInfos()
            node['DOCUMENT_ATTRIBUTES']['CAN_BE_REVISED'] = rootDocBrws.canBeRevised()
            if isRoot:
                node['PRODUCT_ATTRIBUTES']['CAN_BE_REVISED'] = True  # Has already been revised
                engcode = compVals.get('engineering_code')
                if not engcode:  # Has already been revised and contains only document props
                    node['PRODUCT_ATTRIBUTES']['CAN_BE_REVISED'] = False
                    node['DOCUMENT_ATTRIBUTES']['CAN_BE_REVISED'] = True
            compId = compBrws.id
            for relatedNode in node.get('RELATIONS', []):  # Caso grezzo
                recursionUpdate(relatedNode)
            if compId:
                getLinkedDocumentsByComponent(node, compBrws)  # Only if component infos
            else:
                getLinkedDocumentsByDocument(node, rootDocBrws)  # Only for document infos

        recursionUpdate(rootNode, True)
        return json.dumps(rootNode)

    @api.model
    def getCheckedOutAttrs(self, vals):
        outDict = {}
        attrsList, hostname, hostpws = vals
        for fileDict in attrsList:
            outLocalDict = fileDict.copy()
            file_path = fileDict.get('file_path', '')
            docBrwsList = self.getDocumentBrws(fileDict)
            outLocalDict['can_checkout'] = False
            outLocalDict['hostname'] = hostname
            outLocalDict['hostpws'] = hostpws
            outLocalDict['engineering_state'] = ''
            outLocalDict['_id'] = False
            if not docBrwsList:
                outLocalDict['help_checkout'] = _('Unable to find document to check-out. Please save it.')
            else:
                for docBrws in docBrwsList:
                    outLocalDict['_id'] = docBrws.id
                    outLocalDict['engineering_state'] = docBrws.engineering_state
                    flag, msg = docBrws.canCheckOut(showError=False)
                    if flag:
                        outLocalDict['can_checkout'] = True
                    outLocalDict['help_checkout'] = msg
                    break
            outDict[file_path] = outLocalDict
        return outDict

    def open_related_document_revisions(self):
        ir_attachment_ids = self.search([('engineering_code', '=', self.engineering_code)])
        return {'name': _('Attachment Revs.'),
                'res_model': 'ir.attachment',
                'view_type': 'form',
                'view_mode': 'list,form',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', ir_attachment_ids.ids)],
                'context': {}}

    @api.model
    def saveSingleLevel(self, clientArg):
        component_props, document_props, dbThread = clientArg[0]
        host_name = clientArg[1]
        host_pws = clientArg[2]
        #  generate component
        product_product_id = self.env['product.product'].with_context(plm_saving_context=clientArg).createFromProps(
            component_props)
        if not product_product_id:
            logging.warning("Unable to create / get product_product from %s" % component_props)
        #  generate document
        ir_attachment_id, action = self.env['ir.attachment'].with_context(plm_saving_context=clientArg).createFromProps(
            document_props,
            dbThread,
            host_name,
            host_pws)
        if not ir_attachment_id:
            logging.warning("Unable to create / get ir_attachment from %s" % document_props)
        #  generate link
        if product_product_id and ir_attachment_id:
            self.env['plm.component.document.rel'].createFromIds(product_product_id,
                                                                 ir_attachment_id)
        else:
            logging.warning("Unable to generate link from product: %s document: %s Thread %s" % (
            product_product_id, ir_attachment_id, dbThread))
        return (action,
                product_product_id.id if product_product_id else False,
                ir_attachment_id.id if ir_attachment_id else False)

    @api.model
    def createFromProps(self,
                        documentAttribute={},
                        dbThread=False,
                        hostName=False,
                        hostPws=False):
        action = 'upload'
        if documentAttribute.get("CUTTED_COMP", False) or documentAttribute.get("VIRTUAL",
                                                                                False) or documentAttribute.get(
            'ONLY_COMP', False):
            return False, 'jump'
        engineering_code = documentAttribute.get("engineering_code", False)
        if not engineering_code:
            raise UserError("Unable to create document with empty name %r" % (documentAttribute.get('KEY', '')))

        plm_checkout_vals = {'userid': self.env.user.id,
                             'hostname': hostName,
                             'hostpws': hostPws}
        found = False
        ir_attachemnt_id = self.env['ir.attachment']
        for seached_ir_attachemnt_id in self.search([('engineering_code', '=', engineering_code),
                                                     ('engineering_revision', '=',
                                                      documentAttribute.get('engineering_revision', 0))]):
            found = True
            ir_attachemnt_id = seached_ir_attachemnt_id
            plm_checkout_vals['documentid'] = ir_attachemnt_id.id
            break
        documentAttribute['is_library'] = documentAttribute.get('IS_LIBRARY', '')
        documentAttribute['library_path'] = documentAttribute.get('LIBRARY_PATH', '')
        if found:  # write
            if ir_attachemnt_id.engineering_state not in [RELEASED_STATUS, OBSOLATED_STATUS]:
                if ir_attachemnt_id.needUpdate():
                    ir_attachemnt_id.write(documentAttribute)
                    action = ir_attachemnt_id.canIUpload(dbThread)
                else:
                    action = 'jump'
            else:
                action = 'jump'
        else:  # create
            documentAttribute['first_source_path'] = documentAttribute.get('INTEGRATION_ORIG_FILE_PATH', '')
            documentAttribute['cad_name'] = documentAttribute.get('CAD_NAME', '')
            ir_attachemnt_id = ir_attachemnt_id.create(documentAttribute)
            plm_checkout_vals['documentid'] = ir_attachemnt_id.id
            self.env['plm.checkout'].create(plm_checkout_vals)
        return ir_attachemnt_id, action

    def getLastBackupDoc(self):
        for document_id in self:
            return self.env['plm.backupdoc'].search([('documentid', '=', document_id.id)], order='create_date DESC',
                                                    limit=1)
        return False

    def setupCadOpen(self, hostname='', pws_path='', operation_type=''):
        plm_cad_open = self.env['plm.cad.open'].sudo()
        if hostname and pws_path:
            for doc_id in self:
                last_bck = doc_id.getLastBackupDoc()
                plm_cad_open_brws = plm_cad_open.search([('document_id', '=', doc_id.id)])
                plm_cad_open_brws = plm_cad_open.create({
                    'plm_backup_doc_id': last_bck.id,
                    'userid': self.env.user.id,
                    'document_id': doc_id.id,
                    'pws_path': pws_path,
                    'hostname': hostname,
                    'operation_type': operation_type
                })
                return plm_cad_open_brws
        return plm_cad_open

    def setupCadOpenRPC(self, hostname='', pws_path='', operation_type=''):
        ret = self.setupCadOpen(hostname, pws_path, operation_type)
        return ret.ids

    @api.model
    def clientCanIUpload(self, clientArgs):
        ir_attachment_id, dbThread = clientArgs
        return self.browse(ir_attachment_id).canIUpload(dbThread)

    def canIUpload(self, dbTheread):
        action = 'upload'
        plm_dbthread = self.env['plm.dbthread']
        actualdbThred = int(dbTheread)
        for ir_attachment_id in self:
            key = "%s_%s" % (ir_attachment_id.engineering_code, ir_attachment_id.engineering_revision)
            threadCodelist = plm_dbthread.search([('documement_name_version', '=', key),
                                                  ('done', '=', False)]).mapped(lambda x: int(x.threadCode))
            if len(threadCodelist):
                if actualdbThred == max(threadCodelist):
                    break
                if actualdbThred < max(threadCodelist):
                    action = 'jump'
                    break
                # if actualdbThred > min(threadCodelist):
                #     action = 'wait'
                #     break
                break
            else:
                action = 'jump'  # no activity to perform
        return action

    @api.model
    def isDownloadableFromServer(self, args):
        """
        check il the document listed is ready to be downloaded from local server
        """
        forceFlag = False
        ids, listedFiles, selection, _local_server_name = args
        if not selection:
            selection = 1

        if selection < 0:
            forceFlag = True
            selection = selection * (-1)

        if selection == 2:
            docArray = self._getlastrev(ids)
        else:
            docArray = ids
        return self.browse(docArray)._data_get_files(listedFiles,
                                                     forceFlag,
                                                     _local_server_name)

    @api.model
    def GetProductDocumentId(self, clientArgs):
        product_product_id, plm_document_id = self._GetproductDocumentID(clientArgs)
        return (False if not product_product_id else product_product_id.id,
                False if not plm_document_id else plm_document_id.id)

    def _GetproductDocumentID(self, clientArgs):
        componentAtts, documentAttrs = clientArgs
        product_product_id = False
        plm_document_id = False
        engineering_code = componentAtts.get('engineering_code')
        engineering_revision = componentAtts.get('engineering_revision', 0)
        if engineering_code:
            for product_product in self.env['product.product'].search([('engineering_code', '=', engineering_code),
                                                                       ('engineering_revision', '=',
                                                                        engineering_revision)]):
                product_product_id = product_product
                break
        document_name = documentAttrs.get('engineering_code')
        document_revision = documentAttrs.get('engineering_revision', 0)
        if document_name:
            for plm_document in self.env['ir.attachment'].search([('engineering_code', '=', document_name),
                                                                  ('engineering_revision', '=', document_revision)]):
                plm_document_id = plm_document
                break
        return product_product_id, plm_document_id

    def checkNewer(self):
        self.ensure_one()
        for document in self:
            plm_cad_open = self.sudo().env['plm.cad.open'].getLastCadSave(document)
            last_bck = self.env['plm.backupdoc'].getLastBckDocument(document)
            if plm_cad_open.plm_backup_doc_id.id != last_bck.id:
                return True
        return False

    def checkUnlinkCadOpen(self, operation_type, hostname):
        cad_open = self.sudo().env['plm.cad.open']
        for document in self:
            cad_opens = cad_open.search([
                ('document_id', '=', document.id),
                ('operation_type', '=', operation_type),
                ('hostname', '=', hostname)
            ],
                limit=1,
                order='id desc'
            )
            cad_opens.unlink()
        return True

    @api.model
    def GetDocumentInfosFromFileName(self, fileName):
        """
        get info of all the document related with the file name
        """
        out = []
        for ir_attachment_id in self.search([('name', '=', fileName.get('file_name'))]):
            out.append({'id': ir_attachment_id.id,
                        'name': ir_attachment_id.name,
                        'iconStream': ir_attachment_id.preview or '',
                        'engineering_revision': ir_attachment_id.engineering_revision,
                        'engineering_code': ir_attachment_id.engineering_code})
        return out

    @api.model
    def GetAllFiles(self, request, default=None):
        """
            Extract documents to be returned
        """
        forceFlag = False
        listed_models = []
        listed_documents = []
        modArray = []
        oid, listedFiles, selection = request
        if not selection:
            selection = 1

        if selection < 0:
            forceFlag = True
            selection = selection * -1

        kind = 'HiTree'  # Get Hierarchical tree relations due to children
        docArray = self._explodedocs(oid, [kind], listed_models)
        if oid not in docArray:
            docArray.append(oid)  # Add requested document to package
        for item in docArray:
            kinds = ['LyTree', 'RfTree']  # Get relations due to layout connected
            modArray.extend(self._relateddocs(item, kinds, listed_documents))
            modArray.extend(self._explodedocs(item, kinds, listed_documents))
        modArray.extend(docArray)
        docArray = list(set(modArray))  # Get unique documents object IDs
        if selection == 2:
            docArray = self._getlastrev(docArray)
        if oid not in docArray:
            docArray.append(oid)  # Add requested document to package
        return self.browse(docArray)._data_get_files(listedFiles, forceFlag)

    @api.model
    def updatePreviews(self):
        """
            Return a new name due to sequence next number.
        """
        configParamObj = self.env['ir.config_parameter'].sudo()
        paramName = 'LAST_DT_PREVIEW_UPDATE'
        last_update = configParamObj._get_param(paramName) or False
        condition = [('is_plm', '=', True)]
        if last_update and last_update != 'False':
            last_update = datetime.strptime(last_update, DEFAULT_SERVER_DATETIME_FORMAT)
            condition.append(('write_date', '>=', last_update))
        for document_id in self.search(condition):
            if document_id.is3D():
                for product_id in document_id.linkedcomponents:
                    product_id.image_1920 = document_id.preview
                    product_id.product_tmpl_id.image_1920 = document_id.preview
        configParamObj.set_param(paramName, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))

    def checkRelatedModelCheckIn(self, doc2d_id, docArray):
        documentRelation = self.env['ir.attachment.relation']
        doc_rels = documentRelation.search(
            ['|', ('parent_id', '=', doc2d_id), ('child_id', '=', doc2d_id), ('link_kind', '=', 'LyTree')])
        for doc_rel in doc_rels:
            doc3d = False
            child = doc_rel.child_id
            parent = doc_rel.parent_id
            if child.id == doc2d_id:
                doc3d = parent
            else:
                doc3d = child
            if doc3d.id not in docArray and not doc3d.ischecked_in:
                return doc3d
        return True

    @api.model
    def getPlmDTDelta(self):
        configParamObj = self.sudo().env['ir.config_parameter']
        PLM_DT_DELTA = configParamObj._get_param('PLM_DT_DELTA')
        if not PLM_DT_DELTA:
            PLM_DT_DELTA = 10
        else:
            try:
                PLM_DT_DELTA = eval(PLM_DT_DELTA)
            except Exception as ex:
                logging.error('Cannot compute DT delta %r' % (ex))
                PLM_DT_DELTA = 10
        return PLM_DT_DELTA

    @api.model
    def getDocId(self, args):
        docId = args.get('id', False)
        if not docId:
            docName = args.get('engineering_code')
            docRev = args.get('engineering_revision')
            for attachment_id in self.search(
                [('engineering_code', '=', docName), ('engineering_revision', '=', docRev)]):
                return attachment_id
        else:
            return self.browse(docId)
        logging.warning('Document with name "%s" and revision "%s" not found' % (docName, docRev))
        return False

    @api.model
    def CheckIn2(self, request, default=None, force=False):
        if self.CheckInRecursive2(request[0],
                                  default=default,
                                  force=force,
                                  recursive=False):
            return [request[0]]
        return []

    @api.model
    def CheckInRecursive2(self, involved_docs_dict, **kargs):
        """
            Evaluate documents to return
        """
        involved_docs_dict = json.loads(involved_docs_dict)
        for doc_vals in involved_docs_dict.get('to_check_in', []):
            docId = self.getDocId(doc_vals)
            checked = doc_vals.get('checked', False)
            if not docId:
                raise UserError(f'Cannot check-in document with id False. Vals {doc_vals}')
            if checked or kargs.get('force', False):
                checkoutId = self.env['plm.checkout'].search(
                    [('documentid', '=', docId.id), ('userid', '=', self.env.user.id)])
                if checkoutId:
                    checkoutId.unlink()
        return True

    def getLastCadSave(self):
        for ir_attachment_id in self:
            for cad_open in self.env['plm.cad.open'].search([
                ('document_id', '=', ir_attachment_id.id),
                ('operation_type', '=', 'save'),
            ],
                order='create_date DESC', limit=1):
                return cad_open.create_date
            return ir_attachment_id.write_date

    def getDefaulValueDict(self, docBrws, PLM_DT_DELTA, is_root):
        tmp_dict = {}
        tmp_dict['id'] = docBrws.id
        tmp_dict['datas_fname'] = docBrws.name
        tmp_dict['name'] = docBrws.name
        tmp_dict['document_type'] = docBrws.document_type.upper()
        tmp_dict['write_date'] = docBrws.getLastCadSave().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        tmp_dict['check_in'] = docBrws.ischecked_in()
        tmp_dict['check_out_by_me'] = docBrws.isCheckedOutByMe()
        tmp_dict['is_latest_rev'] = docBrws.isLatestRevision()
        tmp_dict['PLM_DT_DELTA'] = PLM_DT_DELTA
        tmp_dict['is_root'] = is_root
        tmp_dict['must_update_from_cad'] = docBrws.must_update_from_cad
        tmp_dict['msg'] = ''
        return tmp_dict

    def fill_up_check_in_status(self, docBrws, PLM_DT_DELTA, is_root):
        out_status = ''
        data_info = self.getDefaulValueDict(docBrws, PLM_DT_DELTA, is_root)
        docBrws._is_checkout()
        if docBrws.is_checkout:
            if docBrws.isCheckedOutByMe():
                data_info['options'] = {'save_and_check_in': _('Save and check-in'),
                                        'keep_and_go': _('Keep check-out'),
                                        'discard': _('Dangerous !! Discard and check-in'),
                                        }
                data_info['msg'] = _('Check-Out by me')
                out_status = 'to_check'
            else:
                data_info['msg'] = _(f'Check-Out by {docBrws.checkout_user}')
                out_status = 'to_info'
        else:
            data_info['msg'] = _('Checked-IN')
            out_status = 'already_checkin'
        return data_info, out_status

    @api.model
    def preCheckInRecursive_all(self,
                                doc_props):
        """
        this funcition is used from the client application
        """
        dict_props = json.loads(doc_props[0])
        odoo_id = dict_props.get('_id', False)
        if not odoo_id:
            root_id = self.getDocId(dict_props)
            if not root_id:
                raise UserError(f"Unable to retrieve information from {doc_props}")
        else:
            root_id = self.browse(odoo_id)
        return json.dumps(self._preCheckInRecursive_all(root_id))

    def _preCheckInRecursive_all(self,
                                 root_id):
        out = {'to_check_2d': [],
               'to_check_3d': [],
               'info': [],
               'root_ent': False
               }
        PLM_DT_DELTA = self.getPlmDTDelta()
        doc_2d_ids = self.env[self._name]
        doc_3d_ids = self.env[self._name]
        #
        for doc_id in self.browse(list(set(self.getRelatedLyTree(root_id.id,
                                                                 getOnyChkOut=True) + \
                                           self.getRelatedPrTree(root_id.id,
                                                                 recursion=True,
                                                                 getOnyChkOut=True)))):
            if doc_id.is3D():
                doc_3d_ids += doc_id
            else:
                doc_2d_ids += doc_id

        if root_id.is3D():
            doc_3d_ids += root_id
            doc_3d_ids += self.browse(self.getRelatedHiTree(root_id.id,
                                                            recursion=True,
                                                           getRftree=True,
                                                           getOnyChkOut=True))
        else:
            doc_2d_ids += root_id
            for doc_id in doc_3d_ids:
                doc_3d_ids += self.browse(self.getRelatedHiTree(doc_id.id,
                                                                recursion=True,
                                                               getRftree=True,
                                                               getOnyChkOut=True))
        for doc_3d_id in doc_3d_ids:
            doc_2d_ids+= self.browse(list(set(self.getRelatedLyTree(doc_3d_id.id,
                                                                    getOnyChkOut=True))))
        done = []
        for s_doc_id in doc_3d_ids + doc_2d_ids:
            if s_doc_id.id in done:
                continue
            done.append(s_doc_id.id)
            data_info, out_status = self.fill_up_check_in_status(s_doc_id,
                                                                 PLM_DT_DELTA,
                                                                 is_root=s_doc_id.id == root_id.id)
            if out_status == 'to_check':
                if data_info['document_type'] in ['2D', 'PR']:
                    out['to_check_2d'].append(data_info)
                elif data_info['document_type'] == '3D':
                    out['to_check_3d'].append(data_info)
            else:
                out['info'].append(data_info)
        return out

    @api.model
    def preCheckInRecursive(self,
                            doc_props,
                            forceCheckInModelByDrawing=True,
                            recursion=True,
                            onlyActiveDoc=False):
        """
        make the check for the check-in operation
        """
        out = {
            'to_check_in': [],
            'to_ask': [],
            'to_block': [],
            'to_info': [],
            'to_check': [],
            'already_checkin': [],
        }
        evaluated = []
        doc_props = json.loads(doc_props)
        doc_id = doc_props.get('_id', False)
        if not doc_id:
            doc_id = self.getDocId(doc_props)
            if not doc_id:
                return out
            else:
                doc_id = doc_id.id

        def setupInfos(out,
                       docBrws,
                       PLM_DT_DELTA,
                       is_root,
                       doc_dict_3d=False):

            def appendItem(resDict, to_append):
                for elem in resDict:
                    if elem['datas_fname'] == to_append['datas_fname']:
                        return
                resDict.append(to_append)

            tmp_dict = {}
            doc_id = docBrws.id
            evaluated.append(doc_id)
            tmp_dict['id'] = docBrws.id
            tmp_dict['datas_fname'] = docBrws.name
            tmp_dict['name'] = docBrws.name
            tmp_dict['document_type'] = docBrws.document_type.upper()
            tmp_dict['write_date'] = docBrws.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            tmp_dict['check_in'] = docBrws.ischecked_in()
            tmp_dict['check_out_by_me'] = docBrws.isCheckedOutByMe()
            tmp_dict['is_latest_rev'] = docBrws.isLatestRevision()
            tmp_dict['children_2d'] = {}
            tmp_dict['children_3d'] = {}
            tmp_dict['children_3d_ref'] = {}
            tmp_dict['PLM_DT_DELTA'] = PLM_DT_DELTA
            tmp_dict['plm_cad_open_newer'] = docBrws.checkNewer()
            tmp_dict['is_root'] = is_root
            tmp_dict['msg'] = ''
            if doc_dict_3d:
                if doc_dict_3d['check_in'] or (not doc_dict_3d['check_in'] and not doc_dict_3d['check_out_by_me']):
                    if doc_dict_3d['plm_cad_open_newer']:
                        doc_dict_3d['msg'] = 'Model %r related to drawing %r is not updated.' % (
                        doc_dict_3d['name'], tmp_dict['name'])
                        appendItem(out['to_block'], doc_dict_3d)
                elif forceCheckInModelByDrawing:
                    msg = 'Model %r related to drawing %r ' % (doc_dict_3d['name'], tmp_dict['name'])
                    if doc_dict_3d['check_in']:
                        msg += "is Checked in"
                    if (not doc_dict_3d['check_in'] and not doc_dict_3d['check_out_by_me']):
                        msg += "is checke-out by %r " % doc_dict_3d['check_out_by_me']
                    elif doc_dict_3d['check_out_by_me']:
                        msg += "is in check-out by you."
                    if doc_dict_3d['plm_cad_open_newer']:
                        msg += 'Cad date not aligned %r ' % doc_dict_3d['plm_cad_open_newer']
                    doc_dict_3d['msg'] = msg
                    appendItem(out['to_block'], doc_dict_3d)
                    if doc_dict_3d in out['to_check']:
                        out['to_check'].remove(doc_dict_3d)
                    if doc_dict_3d in out['to_ask']:
                        out['to_ask'].remove(doc_dict_3d)
                    if doc_dict_3d in out['to_check_in']:
                        out['to_check_in'].remove(doc_dict_3d)
                    return
                else:
                    appendItem(out['to_check'], doc_dict_3d)
                    tmp_dict['options'] = {
                        'discard': 'Discard and check-in',
                        'save_and_check_in': 'Save and check-in',
                        'keep_and_go': 'Keep check-out and check-in children'
                    }
            if is_root:
                if tmp_dict['check_in']:
                    if tmp_dict['plm_cad_open_newer']:
                        tmp_dict['msg'] = 'Document %r already checked-in but not updated.' % (tmp_dict['name'])
                        appendItem(out['to_info'], tmp_dict)
                    else:
                        tmp_dict['checked'] = True
                        appendItem(out['already_checkin'], tmp_dict)
                elif tmp_dict['check_out_by_me']:
                    appendItem(out['to_check'], tmp_dict)
                    tmp_dict['options'] = {
                        'discard': 'Discard and check-in',
                        'save_and_check_in': 'Save and check-in',
                        'keep_and_go': 'Keep check-out and check-in children'
                    }
                else:
                    tmp_dict['msg'] = 'Document %r is in check-out by another user. Cannot check-in.' % (
                    tmp_dict['name'])
                    appendItem(out['to_block'], tmp_dict)
            else:
                if tmp_dict['check_in']:
                    if tmp_dict['plm_cad_open_newer']:
                        tmp_dict['msg'] = 'Document %r already checked-in but not updated.' % (tmp_dict['name'])
                        appendItem(out['to_info'], tmp_dict)
                    else:
                        tmp_dict['checked'] = True
                        appendItem(out['already_checkin'], tmp_dict)
                elif tmp_dict['check_out_by_me']:
                    appendItem(out['to_check'], tmp_dict)
                    tmp_dict['options'] = {
                        'discard': 'Discard and check-in',
                        'save_and_check_in': 'Save and check-in',
                        'keep_and_go': 'Keep check-out and check-in children'
                    }
                else:
                    tmp_dict['msg'] = 'Document %r is in check-out by another user. Cannot check-in, skipped.' % (
                    tmp_dict['name'])
                    appendItem(out['to_info'], tmp_dict)
                    if tmp_dict['plm_cad_open_newer']:
                        tmp_dict['msg'] += '\nDocument %r in check-out by another user and not updated.' % (
                        tmp_dict['name'])
                        appendItem(out['to_info'], tmp_dict)
            return tmp_dict

        def recursionf(doc_id,
                       out,
                       evaluated,
                       PLM_DT_DELTA,
                       is_root=False,
                       forceCheckInModelByDrawing=True,
                       struct_type='3D',
                       recursion=True):
            if doc_id in evaluated:
                return {}
            docs3D = self.browse(doc_id)
            docs2D = self.env['ir.attachment']
            fileType = docs3D.document_type.upper()
            if fileType == '2D':
                setupInfos(out,
                           docs3D,
                           PLM_DT_DELTA,
                           is_root)
                if onlyActiveDoc:
                    return
                is_root = False
                docs3D = self.browse(list(set(self.getRelatedLyTree(docs3D.id))))
            for doc3D in docs3D:
                doc_id_3d = doc3D.id
                if doc_id_3d in evaluated:
                    continue
                doc_dict_3d = setupInfos(out,
                                         doc3D,
                                         PLM_DT_DELTA,
                                         is_root)
                if not doc3D.isCheckedOutByMe():
                    continue
                if struct_type != '3D':
                    docs2D += self.browse(list(set(self.getRelatedLyTree(doc_id_3d))))
                    for doc2d in docs2D:
                        if doc2d.id in evaluated:
                            continue
                        if doc2d.id != doc_id:
                            setupInfos(out,
                                       doc2d,
                                       PLM_DT_DELTA,
                                       is_root,
                                       doc_dict_3d)
                doc3DChildrens = self.browse(self.getRelatedHiTree(doc3D.id,
                                                                   recursion=False))
                for doc3DChildren in doc3DChildrens:
                    if recursion:
                        recursionf(doc3DChildren.id,
                                   out,
                                   evaluated,
                                   PLM_DT_DELTA,
                                   False,
                                   forceCheckInModelByDrawing,
                                   struct_type,
                                   recursion)
                docsReference = self.browse(self.getRelatedRfTree(doc3D.id,
                                                                  recursion=False))
                for doc3DChildrenRef in docsReference:
                    if recursion:
                        recursionf(doc3DChildrenRef.id,
                                   out,
                                   evaluated,
                                   PLM_DT_DELTA,
                                   False,
                                   forceCheckInModelByDrawing,
                                   struct_type,
                                   recursion)

        PLM_DT_DELTA = self.getPlmDTDelta()
        docs3D = self.browse(doc_id)
        struct_type = docs3D.document_type.upper()
        recursionf(doc_id,
                   out,
                   evaluated,
                   PLM_DT_DELTA,
                   True,
                   forceCheckInModelByDrawing,
                   struct_type,
                   recursion)
        return json.dumps(out)

    @api.model
    def preCheckOutRecursive(self, comp_vals):
        comp_vals = json.loads(comp_vals)
        out = []
        for comp_val in comp_vals:
            _comp_fields, doc_fields, _relation_fields = comp_val
            doc_fields['err_msg'] = ''
            doc_name = doc_fields.get('engineering_code', '')
            doc_rev = doc_fields.get('engineering_revision', 0)
            document_ids = self.search([
                ('engineering_code', '=', doc_name),
                ('engineering_revision', '=', doc_rev)
            ])
            for doc_id in document_ids:
                doc_fields['name'] = doc_id.name
                if not doc_id.isLatestRevision():
                    doc_fields['checkout'] = False
                    doc_fields['err_msg'] = 'Document %r is not at latest revision in PWS.' % (doc_fields['name'])
                    out.append(doc_fields)
                    continue
                checkout_by_me = doc_id.isCheckedOutByMe()
                if checkout_by_me:
                    doc_fields['checkout'] = True
                    out.append(doc_fields)
                    continue
                is_check_in = doc_id.ischecked_in()
                if is_check_in:
                    newer_in_odoo = doc_id.checkNewer()
                    if newer_in_odoo:
                        doc_fields['checkout'] = False
                        doc_fields['newer'] = True
                        doc_fields['err_msg'] = 'Document %r is not updated.' % (doc_fields['name'])
                        out.append(doc_fields)
                        continue
                    doc_fields['checkout'] = True
                    out.append(doc_fields)
                else:
                    doc_fields['checkout'] = False
                    doc_fields['err_msg'] = f"Document {doc_fields['name']} is in checkout by {doc_id.checkout_user}."
                    out.append(doc_fields)
        return json.dumps(out)

    @api.model
    def CheckOutRecursive(self, structure, pws_path='', hostname='', force=False):
        stop = False
        structure = json.loads(structure)
        for doc_fields in structure:
            doc_name = doc_fields.get('engineering_code', '')
            doc_rev = doc_fields.get('engineering_revision', 0)
            document_ids = self.search([
                ('engineering_code', '=', doc_name),
                ('engineering_revision', '=', doc_rev)
            ])
            for doc_id in document_ids:
                checkout = doc_fields.get('checkout', False)
                doc_fields['checkout'] = False
                isCheckoutByMe, _checkoutUser = doc_id.checkoutByMeWithUser()
                newer = doc_fields.get('newer', False)
                if newer and force:
                    checkout = True
                if not checkout:
                    stop = True
                if checkout:
                    if isCheckoutByMe:
                        doc_fields['checkout'] = True
                        continue
                    if not stop:
                        checkout_id, msg = doc_id.checkout(hostname, pws_path, showError=False)
                        if not checkout_id or msg:
                            doc_fields['err_msg'] += '\n%s' % (msg)
                        else:
                            doc_id.setupCadOpen(hostname, pws_path, operation_type='check-out')
                            doc_fields['checkout'] = True
                    else:
                        doc_fields['err_msg'] += '\nCannot checkout document %s.' % (doc_fields['name'])
        return json.dumps(structure)

    @api.model
    def getRelatedPkgTreeCount(self, doc_id):
        if not doc_id:
            logging.warning('Cannot get links from %r document' % (doc_id))
            return 0
        to_search = [('link_kind', 'in', ['PkgTree']),
                     ('parent_id', '=', doc_id)]
        return self.env['ir.attachment.relation'].search_count(to_search)

    @api.model
    def cleanZipArchives(self, j_doc_ids):
        out = []
        doc_ids = json.loads(j_doc_ids)
        for doc_id in doc_ids:
            if self.getRelatedPkgTreeCount(doc_id) > 0:
                out.append(doc_id)
        return json.dumps(out)

    def print_Parent_Structure(self):
        # <record id="account_invoices" model="ir.actions.report">
        action = self.env.ref('plm.action_report_parents_structure').report_action(self)
        action.update({'close_on_report_download': True})
        return action

    def print_Document_Doc_Structure(self):
        action = self.env.ref('plm.action_report_doc_structure').report_action(self)
        action.update({'close_on_report_download': True})
        return action

    #
    # client workflow functions
    #
    @api.model
    def action_from_draft_to_draf(self):
        pass

    def getDocBom(self,
                  level=0,
                  recursion=True,
                  report_obj=None):
        for attachment_id in self:
            children_list = []
            if recursion and attachment_id.document_type.upper() not in ['2D']:
                children = attachment_id.getRelatedOneLevelLinks(attachment_id.id, ['RfTree', 'LyTree', 'HiTree'])
                for child_id in children:
                    attachment_child = self.browse(child_id)
                    child_dict = attachment_child.getDocBom(level + 1,
                                                            recursion=False,
                                                            report_obj=report_obj)
                    children_list.append(child_dict)
            product_product_id = None
            for product_product_id in attachment_id.linkedcomponents:
                break
            vals = {'id': attachment_id,
                    'product_id': product_product_id,
                    'level': level,
                    'report_obj': report_obj,
                    'children': children_list}
            break
        return vals

    @api.model
    def sent_check_out_requests(self, document_id):
        """
        create an activity on document asking to check-out the document
        """
        for ir_attachment_id in self.browse([document_id]):
            _id, action, _message = ir_attachment_id.canCheckOut1()
            if action == 'check_out_by_user':
                res_user_id = ir_attachment_id._getCheckOutUser()
                message = _(f"User {self.env.user.display_name} request this document for make some modification")
                todos = {'res_id': ir_attachment_id.id,
                         'res_model_id': self.env['ir.model'].search([('model', '=', self._name)]).id,
                         'user_id': res_user_id.id,
                         'summary': _("Check-In request"),
                         'note': message,
                         'activity_type_id': self.env.ref("plm.mail_activity_check_out_request").id,
                         'date_deadline': datetime.today().date(),
                         }
                self.env['mail.activity'].create(todos)
        return True

    def related_not_update(self):
        for attachment_id in self:
            relation_ids = self.env['ir.attachment.relation'].search(["|", ('parent_id', '=', attachment_id.id),
                                                                      ('child_id', '=', attachment_id.id),
                                                                      ('link_kind', '=', 'LyTree')])
            return {'name': _('Attachment Relations.'),
                    'res_model': 'ir.attachment.relation',
                    'view_type': 'form',
                    'view_mode': 'kanban,list,form',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', relation_ids.ids)],
                    'context': {}}

    def open_related_dbthread(self):
        plm_dbthread = self.env['plm.dbthread']
        plm_dbthread_ids = []
        #
        for ir_attachment_id in self:
            search_name = f"{ir_attachment_id.engineering_code}_{ir_attachment_id.engineering_revision}"
            plm_dbthread_ids = plm_dbthread.search([('documement_name_version', '=', search_name)])
        #
        return {'name': _('Saving Error'),
                'res_model': 'plm.dbthread',
                'view_type': 'form',
                'view_mode': 'list',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', plm_dbthread_ids.ids)],
                'context': {}}

    @api.model
    def fillUpClonedStructure(self, args):
        """
        fill up the structure with the missing elements like layout
        """
        def _recursion(cad_structure):
            #
            parent_attrs, children_attrs_structure = cad_structure
            configuration_name = parent_attrs.get('product',{}).get('CONFIGURATION_NAME','')
            product_product_id, attachment_id = self._GetproductDocumentID(tuple(parent_attrs.values()))
            parent_attrs = self.get_clone_info_attr(attachment_id,
                                                    product_product_id)
            parent_attrs['CONFIGURATION_NAME'] = configuration_name
            #
            # Collect missing layout
            #
            children = []
            for doc_id_2d in self.getRelatedLyTree(attachment_id,
                                                   optional_return_type=['2d']):
                layout_data = self.get_clone_info_attr(doc_id_2d)
                if 'layouts' in parent_attrs:
                    parent_attrs['layouts'].append(layout_data)
                else:
                    parent_attrs['layouts']=[layout_data]
            #
            # Collect children missing layouts
            #
            for child_attrs_structure in children_attrs_structure:
                children.append(_recursion(child_attrs_structure))
            #
            return (parent_attrs, children)
        
        return json.dumps(_recursion(json.loads(args[0])))
    
    def get_clone_info_attr(self,
                            doc_id, 
                            product_product_id=None):
            def get_dict(product_product_id):
                return {
                        'engineering_code': product_product_id.engineering_code,
                        'engineering_revision': product_product_id.engineering_revision,
                        'name':product_product_id.name,
                        'id':product_product_id.id
                        }
            #
            if not isinstance(doc_id, models.Model):
                ir_attachment=self.browse(doc_id)
            else:
                ir_attachment=doc_id
            #
            if product_product_id:
                product_dict=get_dict(product_product_id)
            else:
                product_dict={}
                for product_product_id in ir_attachment.linkedcomponents:
                    product_dict=get_dict(product_product_id)
                    break
            #
            return {'document':{
                                'engineering_code': ir_attachment.engineering_code,
                                'engineering_revision': ir_attachment.engineering_revision,
                                'name':ir_attachment.name,
                                'id':ir_attachment.id,
                                'document_type':ir_attachment.document_type
                                },
                    'product':product_dict
                }

    @api.model
    def getCloneStructure(self,
                          args):
        #
        logging.warning("Function getClonedStructure will be removed in the new verison !!")
        #
        SUPPORT_MAIN_PRODUCT_ATTRIBUTES = [
            'CONFIGURATION_NAME',
            'CONFIGURATIONS',
            'INTEGRATION_FILE_TYPE',
        ]

        #
        def getProduct_dict(product_product_id):
            return {
                'engineering_code': product_product_id.engineering_code,
                'engineering_revision': product_product_id.engineering_revision,
                'name': product_product_id.name,
                'id': product_product_id.id
            }

        json_main_root_attributes, cloneRelatedDocuments = args

        #
        def get_clone_info_attr(doc_id, product_product_id=None):
            ir_attachment = self.browse(doc_id)
            if product_product_id:
                product_dict = getProduct_dict(product_product_id)
            else:
                product_dict = {}
                for product_product_id in ir_attachment.linkedcomponents:
                    product_dict = getProduct_dict(product_product_id)
                    break

            return {'document': {
                'engineering_code': ir_attachment.engineering_code,
                'engineering_revision': ir_attachment.engineering_revision,
                'name': ir_attachment.name,
                'id': ir_attachment.id,
                'document_type': ir_attachment.document_type
            },
                'product': product_dict
            }

        #
        out = {'MAIN': {},
               'RF': [],
               'LF': []}
        main_root_attributes = json.loads(json_main_root_attributes)
        product_product_id, attachment_id = self._GetproductDocumentID(tuple(main_root_attributes.values()))
        #
        if attachment_id:
            #
            doc_ids_2d = []
            #
            main_parent_attrs = get_clone_info_attr(attachment_id.id, product_product_id)
            out['MAIN'] = main_parent_attrs
            for k in SUPPORT_MAIN_PRODUCT_ATTRIBUTES:
                out['MAIN']['product'][k] = main_root_attributes.get('product', {}).get(k, '')
            #
            for doc_id in self.getRelatedRfTree(attachment_id.id):
                sub_attrs = get_clone_info_attr(doc_id)
                out['RF'].append((main_parent_attrs,
                                  sub_attrs))
                for doc_id_2d in self.getRelatedLyTree(doc_id,
                                                       optional_return_type=['2d']):
                    doc_ids_2d.append((sub_attrs, doc_id_2d))
            #
            for doc_id_2d in self.getRelatedLyTree(attachment_id.id,
                                                   optional_return_type=['2d']):
                doc_ids_2d.append((main_parent_attrs, doc_id_2d))
                #
            for parent_attrs, doc_id in doc_ids_2d:
                out['LF'].append((parent_attrs,
                                  get_clone_info_attr(doc_id)))
        #

        return json.dumps(out)

    @api.model
    def GetCloneDocumentValues(self, args):
        """
            return the new attributes to be used for cloning the document
        """
        old_product_attrs, old_attachment_attrs, new_product_attrs = args
        out_attachment_value = json.loads(old_attachment_attrs)
        new_product_attrs = json.loads(new_product_attrs)
        if hasattr(self, "customGetCloneDocumentValues"):
            #
            # If you implement the customGetCloneDocumentValues this call will be used to customize the value of the new cloned document from the client clone action
            #
            out_attachment_value = self.customGetCloneDocumentValues(out_attachment_value,
                                                                     json.loads(old_product_attrs),
                                                                     new_product_attrs)
        else:
            #
            engineering_code = new_product_attrs.get('engineering_code', '')
            if engineering_code:
                out_attachment_value[
                    'engineering_code'] = f"{engineering_code}-{self.env['ir.sequence'].next_by_code('ir.attachment.progress')}"
            else:
                out_attachment_value[
                    'engineering_code'] = f"{self.env['ir.sequence'].next_by_code('ir.attachment.progress')}"
            out_attachment_value['engineering_revision'] = 0
            #
            _, exte = os.path.splitext(out_attachment_value['name'])
            out_attachment_value['name'] = f"{out_attachment_value['engineering_code']}{exte}"
        #
        del out_attachment_value['id']
        #
        return json.dumps(out_attachment_value)

    @api.model
    def CheckInById(self, doc_id):
        docBrwsList = self.browse(doc_id)
        for docBrws in docBrwsList:
            docBrws._check_in()
            return docBrws.id
        return False

    def check_attachment_change_impact(self):
        self.ensure_one()
        report_data = {}
        report_data["active_id"] = self.id

        return self.env.ref(
            'plm.action_report_attachment_change_impact'
        ).report_action(docids=[self.id],
                        data=report_data)

    def getRelatedLyTreeNew(self, 
                            optional_return_type=['3d'],
                            getOnyChkOut=False,
                            latest=False):
        """
        """
        #
        self.ensure_one()
        #
        out = self.env['ir.attachment']
        #
        parent_doc_type = self.document_type
        to_search = [('link_kind', 'in', ['LyTree']),
                     '|',
                     ('parent_id', '=', self.id),
                     ('child_id', '=', self.id)]
        doc_rel_ids = self.env['ir.attachment.relation'].search(to_search)
        #
        for doc_rel_id in doc_rel_ids:
            if parent_doc_type == '3d':
                if doc_rel_id.parent_id.id == self.id and doc_rel_id.child_id.document_type == '2d':
                    if latest:
                        child = doc_rel_id.child_id.get_latest_version()[0]
                    else:
                        child = doc_rel_id.child_id
                    if child.id in out.ids:
                        continue
                    out+=child
                elif doc_rel_id.child_id.id == self.id and doc_rel_id.parent_id.document_type == '2d':
                    if latest:
                        parent = doc_rel_id.parent_id.get_latest_version()[0]
                    else:
                        parent = doc_rel_id.parent_id
                    if parent.id in out.ids:
                        continue
                    out+=parent
            elif parent_doc_type == '2d':
                if doc_rel_id.parent_id.id == self.id and doc_rel_id.child_id.document_type in optional_return_type:
                    if latest:
                        child = doc_rel_id.child_id.get_latest_version()[0]
                    else:
                        child = doc_rel_id.child_id
                    if child.id in out.ids:
                        continue
                    out+=child
                elif doc_rel_id.child_id.id == self.id and doc_rel_id.parent_id.document_type in optional_return_type:
                    if latest:
                        parent = doc_rel_id.parent_id.get_latest_version()[0]
                    else:
                        parent = doc_rel_id.parent_id
                    if parent.id in out.ids:
                        continue
                    out+=parent
        return out

    @api.model
    def getRelatedHiTreeNew(self,
                            recursion=True, 
                            getRftree=False,
                            getOnyChkOut=False,
                            latest=False):
        '''
            Get children HiTree documents
        '''
        #
        self.ensure_one()
        #
        out = {"data":self.env['ir.attachment']}
        #
        def _getRelatedHiTree(attachment_id, 
                              recursion, 
                              getRftree):
            if latest:
                attachment_id=attachment_id.get_latest_version()[0]
            children_attachment_ids = self.env['ir.attachment.relation'].search([
                                                        ('link_kind', '=', 'HiTree'),
                                                        ('parent_id', '=', attachment_id.id)])
            for child_attachment_id in children_attachment_ids:
                child_id = child_attachment_id.child_id
                if latest:
                    child_id=child_id.get_latest_version()[0]
                if child_id.id in out['data'].ids:
                    logging.warning('Document %r document already found' % (child_id))
                    continue
                out['data']+=child_id
                if recursion:
                    _getRelatedHiTree(child_id,
                                      recursion,
                                      getRftree)
            if getRftree:
                for obj in self.getRelatedRfTreeNew(recursion=True, 
                                                    evaluated=[],
                                                    latest=latest):
                    out['data']+=obj
        _getRelatedHiTree(self, 
                          recursion, 
                          getRftree)
        return out['data']

    @api.model
    def getRelatedRfTreeNew(self, 
                            recursion=True, 
                            evaluated=False,
                            latest=False):
        #
        self.ensure_one()
        if not evaluated:
            evaluated = self.env['ir.attachment']
        #
        out = self.env['ir.attachment']
        #
        doc_rel_ids = self.env['ir.attachment.relation'].search([('link_kind', 'in', ['RfTree']),
                                                                 ('parent_id', '=', self.id)])
        if self.id in evaluated.ids:
            logging.warning('Document %r already found in RfTree evaluated %r' % (self, evaluated))
            return out
        evaluated+=self
        #
        for doc_rel_id in doc_rel_ids:
            if latest:
                child_id = doc_rel_id.child_id.get_latest_version()[0]
                parent_id = doc_rel_id.parent_id.get_latest_version()[0]
            else:
                child_id = doc_rel_id.child_id
                parent_id = doc_rel_id.parent_id
            #
            if child.id == self.id:
                out+=parent_id
                if recursion:
                    for obj in self.getRelatedRfTreeNew(parent_id, 
                                                        recursion, 
                                                        evaluated,
                                                        latest):
                        out = obj
            else:
                out+=child_id
                if recursion:
                    for obj in self.getRelatedRfTreeNew(child_id, 
                                                        recursion, 
                                                        evaluated,
                                                        latest):
                        out = obj
        return out
#
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

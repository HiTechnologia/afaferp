import logging
from datetime import datetime
import os
import json

from odoo import models
from odoo import fields
from odoo import api
from odoo import _

from odoo.addons.plm.models.plm_mixin import START_STATUS
from odoo.addons.plm.models.plm_mixin import CONFIRMED_STATUS
from odoo.addons.plm.models.plm_mixin import RELEASED_STATUS
from odoo.addons.plm.models.plm_mixin import UNDER_MODIFY_STATUS
from odoo.addons.plm.models.plm_mixin import PLM_NO_WRITE_STATE
from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS

from odoo.exceptions import ValidationError
from odoo.exceptions import AccessError
from odoo.exceptions import UserError
import odoo.tools as tools
from odoo.osv import expression

_logger = logging.getLogger(__name__)

def emptyStringIfFalse(value):
    """
        return an empty string if the value is False
    """
    if value:
        return str(value)
    else:
        return ''


class ProductProduct(models.Model):
    _name='product.product'
    _inherit = ['product.product']
    _description ="Product Product"

    def check_product_change_impact(self):
        self.ensure_one()
        report_data = {}
        bomobj = self.env['mrp.bom']
        rel_datas, prt_datas, relation_datas = bomobj.get_where_used([self.id])
        report_data["active_id"] = self.id
        report_data["prt_datas"] = prt_datas
        return self.env.ref('plm.action_report_product_change_impact').report_action(docids=[self.id], data=report_data)

    def onchange(self, values, field_names, fields_spec):
        values = self.plm_sanitize(values)
        if 'product_tmpl_id' in values:
            del values['product_tmpl_id']
        return super(ProductProduct, self).onchange(values, field_names, fields_spec)

    def action_show_reference(self):
        localCtx = self.env.context.copy()
        ir_attachment_id = localCtx.get('ir_attachment_id')
        return {'type': 'ir.actions.act_window',
                'name': _('Document'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref("plm.view_attachment_form_plm_hinerit").id,
                'res_model': 'ir.attachment',
                'target': 'new',
                'res_id': ir_attachment_id,
                'context': localCtx,
                }

    def _father_part_compute(self, name='', arg={}):
        """ Gets father bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        bom_line_objType = self.env['mrp.bom.line']
        prod_objs = self.browse(self.ids)
        for prod_obj in prod_objs:
            prod_ids = []
            bom_line_objs = bom_line_objType.search([('product_id', '=', prod_obj.id)])
            for bom_line_obj in bom_line_objs:
                for objPrd in self.search([('product_tmpl_id', '=', bom_line_obj.bom_id.product_tmpl_id.id)]):
                    prod_ids.append(objPrd.id)
            prod_obj.father_part_ids = prod_ids

    tmp_material = fields.Many2one('plm.material',
                                   _('Raw Material'),
                                   required=False,
                                   help=_("Select raw material for current product"))
    tmp_surface = fields.Many2one('plm.finishing',
                                  _('Surface Finishing'),
                                  required=False,
                                  help=_("Select surface finishing for current product"))
    tmp_treatment = fields.Many2one('plm.treatment',
                                    _('Thermal Treatment'),
                                    required=False,
                                    help=_("Select thermal treatment for current product"))
    father_part_ids = fields.Many2many('product.product',
                                       compute=_father_part_compute,
                                       string=_("BoM Hierarchy"),
                                       store=False)
    create_date = fields.Datetime(_('Date Created'),
                                  readonly=True)
    write_date = fields.Datetime(_('Date Modified'),
                                 readonly=True)
    std_description = fields.Many2one('plm.description',
                                      _('Standard Description'),
                                      required=False,
                                      default=False,
                                      help=_("Select standard description for current product."))
    std_umc1 = fields.Char(_('UM / Feature 1'),
                           size=32,
                           default='',
                           help=_("Allow to specify a unit measure for the first feature."))
    std_value1 = fields.Float(_('Value 1'),
                              default=0,
                              help=_("Assign value to the first characteristic."))
    std_umc2 = fields.Char(_('UM / Feature 2'),
                           size=32,
                           default='',
                           help=_("Allow to specify a unit measure for the second feature."))
    std_value2 = fields.Float(_('Value 2'),
                              default=0,
                              help=_("Assign value to the second characteristic."))
    std_umc3 = fields.Char(_('UM / Feature 3'),
                           size=32,
                           default='',
                           help=_("Allow to specifiy a unit measure for the third feature."))
    std_value3 = fields.Float(_('Value 3'),
                              default=0,
                              help=_("Assign value to the second characteristic."))

    desc_modify = fields.Text(_('Modification Description'), default='')
    source_product = fields.Many2one('product.product', _('Generated From'))
    # Don't overload std_umc1, std_umc2, std_umc3 setting them related to std_description because odoo try to set value
    # of related fields and integration users doesn't have write permissions in std_description. The result is that
    # integration users can't create products if in changed values there is std_description

    show_std_field1 = fields.Boolean(_('Show std field 1'),
                                 compute='_computeStd')
    show_std_field2 = fields.Boolean(_('Show std field 2'),
                                 compute='_computeStd')
    show_std_field3 = fields.Boolean(_('Show std field 3'),
                                 compute='_computeStd')

    readonly_std_umc1 = fields.Boolean(_("put readOnly the field standard description 1"))
    readonly_std_umc2 = fields.Boolean(_("put readOnly the field standard description 2"))
    readonly_std_umc3 = fields.Boolean(_("put readOnly the field standard description 3"))

    linkeddocuments = fields.Many2many('ir.attachment',
                                       'plm_component_document_rel',
                                       'component_id',
                                       'document_id',
                                       _('Linked Docs'),
                                       ondelete='cascade')

    kit_bom = fields.Boolean(_('KIT Bom Type'))

    def _computeStd(self):
        for product_product_id in self:
            product_product_id.show_std_field1 = False
            product_product_id.show_std_field2 = False
            product_product_id.show_std_field3 = False
            if product_product_id.std_description:
                if product_product_id.std_description.umc1 or product_product_id.std_description.fmt1:
                    product_product_id.show_std_field1 = True
                if product_product_id.std_description.umc2 or product_product_id.std_description.fmt2:
                    product_product_id.show_std_field2 = True
                if product_product_id.std_description.umc3 or product_product_id.std_description.fmt3:
                    product_product_id.show_std_field3 = True

    @api.onchange("std_description")
    def _showStd(self):
        for product_product_id in self:
            product_product_id.show_std_field1 = False
            product_product_id.show_std_field2 = False
            product_product_id.show_std_field3 = False
            product_product_id.readonly_std_umc1 = False
            product_product_id.readonly_std_umc2 = False
            product_product_id.readonly_std_umc3 = False
            std_description = product_product_id.std_description
            if std_description:
                product_product_id.std_umc1 = std_description.umc1
                product_product_id.std_umc2 = std_description.umc2
                product_product_id.std_umc3 = std_description.umc3
                #
                if product_product_id.std_umc1:
                    product_product_id.readonly_std_umc1=True
                    product_product_id.show_std_field1 = True
                else:
                    product_product_id.std_value1 = False

                if product_product_id.std_umc2:
                    product_product_id.readonly_std_umc2=True
                    product_product_id.show_std_field2 = True
                else:
                    product_product_id.std_value2 = False
                if product_product_id.std_umc3:
                    product_product_id.readonly_std_umc3=True
                    product_product_id.show_std_field3 = True
                else:
                    product_product_id.std_value3 = False
                #
            product_product_id.on_change_stdvalue()

    @api.onchange('std_value1', 'std_value2', 'std_value3', 'std_umc1','std_umc2','std_umc3')
    def on_change_stdvalue(self):
        if self.std_description:
            self.name = self.computeDescription(self.std_description,
                                                self.std_umc1,
                                                self.std_umc2,
                                                self.std_umc3,
                                                self.std_value1,
                                                self.std_value2,
                                                self.std_value3)

    @api.onchange('tmp_material')
    def on_change_tmpmater(self):
        if self.tmp_material:
            if self.tmp_material.name:
                self.engineering_material = self.tmp_material.name

    @api.onchange('tmp_surface')
    def on_change_tmpsurface(self):
        if self.tmp_surface:
            if self.tmp_surface.name:
                self.engineering_surface = str(self.tmp_surface.name)

    @api.onchange('tmp_treatment')
    def on_change_tmptreatment(self):
        if self.tmp_treatment:
            if self.tmp_treatment.name:
                self.engineering_treatment = str(self.tmp_treatment.name)

    @api.model
    def getParentBomStructure(self, filterBomType=''):
        bom_line_filter = [('product_id', '=', self.id)]
        if filterBomType:
            bom_line_filter.append(('type', '=', filterBomType))
        mrpBomLines = self.env['mrp.bom.line'].search(bom_line_filter)
        out = []
        for mrpBomLine in mrpBomLines:
            out.append((self.env['mrp.bom'].where_used_header(mrpBomLine),
                        mrpBomLine.bom_id.get_where_used_structure(filterBomType)))
        return out

    @api.model
    def getLatestReleasedRevision(self):
        for product_id in self.search([('engineering_code', '=', self.engineering_code)], order="engineering_code desc"):
            if product_id.id != self.id:
                if product_id.engineering_state in [RELEASED_STATUS, 'undermodifie']:
                    return product_id
        return self

#   Internal methods
    def _packfinalvalues(self, fmt, value=False, value2=False, value3=False):
        """
            Pack a string formatting it like specified in fmt
            mixing both label and value or only label.
        """
        retvalue = ''
        if value3:
            if isinstance(value3, float):
                svalue3 = "%g" % value3
            else:
                svalue3 = value3
        else:
            svalue3 = ''

        if value2:
            if isinstance(value2, float):
                svalue2 = "%g" % value2
            else:
                svalue2 = value2
        else:
            svalue2 = ''

        if value:
            if isinstance(value, float):
                svalue = "%g" % value
            else:
                svalue = value
        else:
            svalue = ''

        if svalue or svalue2 or svalue3:
            cnt = fmt.count('%s')
            if cnt == 3:
                retvalue = fmt % (svalue, svalue2, svalue3)
            if cnt == 2:
                retvalue = fmt % (svalue, svalue2)
            elif cnt == 1:
                retvalue = fmt % (svalue)
        return retvalue

    def getParentBom(self, filterBomType='normal'):
        for product_product_id in self:
            bom_line_filter = [('product_id', '=', product_product_id.id),
                               ('type', '=', filterBomType)]

            mrp_bom_line_ids = self.env['mrp.bom.line'].search(bom_line_filter,
                                                               limit=1)
            for mrp_bom_line_id in mrp_bom_line_ids:
                if product_product_id.id!=mrp_bom_line_id.bom_id.product_tmpl_id.product_variant_id.id:
                    return mrp_bom_line_id.bom_id
        return self.env['mrp.bom']

    def _packvalues(self, fmt, label=False, value=False):
        """
            Pack a string formatting it like specified in fmt
            mixing both label and value or only label.
        """
        retvalue = ''
        if fmt is False:
            return retvalue
        if value:
            if isinstance(value, float):
                svalue = "%g" % value
            else:
                svalue = value
        else:
            svalue = ''

        if label:
            if isinstance(label, float):
                slabel = "%g" % label
            else:
                slabel = label
        else:
            slabel = ''

        if svalue:
            cnt = fmt.count('%s')
            if cnt == 2:
                retvalue = fmt % (slabel, svalue)
            elif cnt == 1:
                retvalue = fmt % (svalue)
            elif cnt == 0 and fmt:
                retvalue = fmt
        return retvalue

    def computeDescription(self, thisObject, std_umc1, std_umc2, std_umc3, std_value1, std_value2, std_value3):
        description1 = False
        description2 = False
        description3 = False
        description = thisObject.description or thisObject.name or 'ERROR !!'
        if thisObject.fmtend:
            if std_umc1 and std_value1:
                description1 = self._packvalues(thisObject.fmt1, std_umc1, std_value1)
            if std_umc2 and std_value2:
                description2 = self._packvalues(thisObject.fmt2, std_umc2, std_value2)
            if std_umc3 and std_value3:
                description3 = self._packvalues(thisObject.fmt3, std_umc3, std_value3)
            description = description + " " + self._packfinalvalues(thisObject.fmtend, description1, description2, description3)
        else:
            if std_umc1 and std_value1:
                description = description + " " + self._packvalues(thisObject.fmt1, std_umc1, std_value1)
            if std_umc2 and std_value2:
                description = description + " " + self._packvalues(thisObject.fmt2, std_umc2, std_value2)
            if std_umc3 and std_value3:
                description = description + " " + self._packvalues(thisObject.fmt3, std_umc3, std_value3)
        if thisObject.unitab:
            description = description + " " + thisObject.unitab
        return description

    def product_template_open(self):
        product_id = self.product_tmpl_id.id
        mod_obj = self.env['ir.model.data']
        search_res = mod_obj.get_object_reference('plm', 'product_template_form_view_plm_custom')
        form_id = search_res and search_res[1] or False
        if product_id and form_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Product Engineering'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.template',
                'res_id': product_id,
                'views': [(form_id, 'form')],
            }

    #def open_report_component(self):
    #    action = self.env.ref('plm.action_report_prod_structure').report_action(self)
    #    action.update({'close_on_report_download': True})
    #    return action

    def open_boms(self):
        product_tmpl_id = self.product_tmpl_id.id
        if product_tmpl_id:
            localCtx = self.env.context.copy()
            localCtx.update({'default_product_tmpl_id': product_tmpl_id,
                             'search_default_product_tmpl_id': product_tmpl_id})
            return {'type': 'ir.actions.act_window',
                    'name': _('Mrp Bom'),
                    'view_type': 'form',
                    'view_mode': 'list,form',
                    'res_model': 'mrp.bom',
                    'context': localCtx,
                    }

    @api.model
    def _getChildrenBom(self,
                        product_product_id,
                        level=0,
                        currlevel=0,
                        bom_type=False):
        """
            Return a flat list of each child, listed once, in a Bom
            :level = [ 0 one level only, 1 all levels]
            :currlevel starting level for the bom
            :bom_type type bom calculation
        """
        #
        computed=[]
        #
        def get_flat_children(product_product_id,
                              level=0,
                              currlevel=0,
                              bom_type=False):
            if currlevel > 1 and level == 0:
                return []
            if product_product_id.id in computed:
                return []
            computed.append(product_product_id.id)
            out = [product_product_id.id]
            for bomid in product_product_id.product_tmpl_id.bom_ids:
                if bom_type and bomid.type != bom_type:
                    continue
                for bomline in bomid.bom_line_ids:
                    children_product_product_ids = get_flat_children(product_product_id=bomline.product_id,
                                                                     level=level,
                                                                     currlevel=currlevel + 1,
                                                                     bom_type=bom_type)
                    out.extend(children_product_product_ids)
            return out
        #
        result = get_flat_children(product_product_id,
                                   level,
                                   currlevel,
                                   bom_type)
        return list(set(result))

    def getLeafBom(self, bom_type='normal'):
        """
        get only the leaf of the bom
        :product_product_id <product_product>
        :bom_type ['normal','kit','engineering']
        :return: [<product_product>,]
        """
        out = []
        computed_bom = []
        def _getLeafBom(parent_product_ids, bom_type='normal'):
            for product_product_id in parent_product_ids:
                has_bom=False
                for mrp_bom_id in product_product_id.product_tmpl_id.bom_ids.filtered(lambda x : x.type==bom_type):
                    has_bom=True
                    if mrp_bom_id in computed_bom:
                        continue
                    else:
                        computed_bom.append(mrp_bom_id)
                    for product_id in mrp_bom_id.bom_line_ids.mapped("product_id"):
                        _getLeafBom(product_id,bom_type=bom_type)
                if not has_bom and product_product_id not in out:
                    out.append(product_product_id)
        _getLeafBom(self)
        return out

    def summarize_level(self, recursion=False, flat=False, level=1, summarize=False, parentQty=1, bom_type=False):
        out = {}
        for product_product_id in self:
            for bom_id in product_product_id.product_tmpl_id.bom_ids:
                if bom_type:
                    if bom_id.type != bom_type:
                        continue
                out[bom_id] = bom_id.summarize_level(recursion, flat, level, summarize, parentQty, bom_type)
        return out

    @api.model
    def RegMessage(self, request, default=None):
        """
            Registers a message for requested component
        """
        oid, message = request
        self.browse([oid]).message_post(body=_(message))
        return False

    @api.model
    def getLastTime(self, oid, default=None):
        return self.getUpdTime(self.browse(oid))

    def getUpdTime(self, obj):
        if(obj.write_date is not False):
            return obj.write_date
        else:
            return obj.create_date

    def Clone(self, defaults={}):
        exitValues = {}
        newCompBrws = self.copy(defaults)
        if newCompBrws not in (None, False):
            exitValues['_id'] = newCompBrws.id
            exitValues['name'] = newCompBrws.name
            exitValues['engineering_code'] = newCompBrws.engineering_code
            exitValues['engineering_revision'] = newCompBrws.engineering_revision
        return exitValues

    @api.model
    def GetUpdated(self, vals):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        partData, attribNames, forceCADProperties = vals
        ids = self.GetLatestIds(partData, forceCADProperties=forceCADProperties)
        return self.browse(list(set(ids))).read(attribNames)

    @api.model
    def GetLatestIds(self, vals, forceCADProperties=False):
        """
            Get Last/Requested revision of given items (by name, revision, update time)
        """
        ids = []
        plmDocObj = self.env['ir.attachment']

        def getCompIds(partName, partRev):
            if docRev is None or docRev is False:
                partIds = self.search([('engineering_code', '=', partName)],
                                      order='engineering_revision').ids
                if len(partIds) > 0:
                    ids.append(partIds[-1])
            else:
                ids.extend(self.search([('engineering_code', '=', partName),
                                        ('engineering_revision', '=', partRev)]).ids)

        for docName, docRev, docIdToOpen in vals:
            docBrw = plmDocObj.browse(docIdToOpen)
            checkOutUser = docBrw.get_checkout_user()
            if checkOutUser:
                isMyDocument = docBrw.isCheckedOutByMe()
                if isMyDocument and forceCADProperties:
                    return []    # Document properties will be not updated
                else:
                    getCompIds(docName, docRev)
            else:
                getCompIds(docName, docRev)
        return list(set(ids))

    @api.model
    def ConvertToPlmProduct(self, attributes_list=[]):
        """
        convert the attributes vals and add the plm id to the array
        """
        out = []
        for attributes in attributes_list:
            engineering_code = attributes.get('engineering_code', False)
            engineering_revision = attributes.get('engineering_revision', 0)
            if engineering_code:
                product_product_id = self.search([('engineering_code', '=', engineering_code),
                                                  ('engineering_revision', '=', engineering_revision)], order='engineering_revision ASC')
                if not product_product_id:
                    product_product_id = self.create(attributes)
                attributes['plm_id'] = product_product_id.id
                out.append(attributes)
        return out

    @api.model
    def SaveOrUpdate(self, vals):
        """
            Save or Update Parts
        """
        listedParts = []
        retValues = []
        for partVals in vals:
            hasSaved = False
            if partVals.get('engineering_code', '') in listedParts:
                continue
            if 'engineering_code' not in partVals:
                partVals['componentID'] = False
                partVals['hasSaved'] = hasSaved
                retValues.append(partVals)
                continue
            existingCompBrwsList = self.search([('engineering_code', '=', partVals['engineering_code']),
                                                ('engineering_revision', '=', partVals.get('engineering_revision', 0))], order='engineering_revision ASC')
            if not existingCompBrwsList:
                existingCompBrwsList = [self.create(partVals)]
                hasSaved = True
            for existingCompBrws in existingCompBrwsList:
                if not hasSaved:
                    partVals['name'] = existingCompBrws.name
                    if self._iswritable(existingCompBrws):
                        hasSaved = True
                        existingCompBrws.write(partVals)
                        weight = partVals.get('weight')
                        if (weight):
                            if not self.write({'weight': weight}):
                                raise UserError(_("Part %r cannot be updated" % (partVals['engineering_code'])))
                        else:
                            logging.warning("No Weight property set unable to update !!")
                partVals['componentID'] = existingCompBrws.id
                partVals['hasSaved'] = hasSaved
                break
            retValues.append(partVals)
            listedParts.append(partVals['engineering_code'])
        return retValues

    @api.model
    def QueryLast(self, request=([], []), default=None):
        """
            Query to return values based on columns selected.
        """
        objId = False
        expData = []
        queryFilter, columns = request
        if len(columns) < 1:
            return expData
        if 'engineering_revision' in queryFilter:
            del queryFilter['engineering_revision']
        allIDs = self.search(queryFilter,
                             order='engineering_revision').ids
        if len(allIDs) > 0:
            allIDs.sort()
            objId = allIDs[len(allIDs) - 1]
        if objId:
            tmpData = self.export_data([objId], columns)
            if 'datas' in tmpData:
                expData = tmpData['datas']
        return expData

    @api.model
    def _summarizeBom(self, datarows):
        dic = {}
        for datarow in datarows:
            key = str(datarow.product_id.id)
            if key in dic:
                dic[key].product_qty = float(dic[key].product_qty) + float(datarow.product_qty)
            else:
                dic[key] = datarow
        retd = list(dic.values())
        return retd

    def _get_recursive_parts(self, include_statuses):
        """
           Get all ids related to current one as children
        """
        out_product =  self.env['product.product']
        errors = []
        tobeReleasedIDs = []
        if not isinstance(self.ids, (list, tuple)):
            self.ids = [self.ids]
        tobeReleasedIDs.extend(self.ids)
        for prodBrws in self:
            for childProdBrws in self.browse(self._getChildrenBom(prodBrws, 1)).filtered(lambda x: x.engineering_code not in [False, ''] and x.engineering_state in include_statuses):
                if childProdBrws.id not in tobeReleasedIDs:
                    out_product+=childProdBrws
        msg = ''
        if errors:
            msg = _("Unable to perform workFlow action due")
            for subMsg in errors:
                msg = msg + "\n" + subMsg
        return (msg, out_product.union())

    def action_create_normalBom_WF(self):
        """
            Create a new Normal Bom if doesn't exist (action callable from code)
        """
        for prodId in self.ids:
            processedIds = []
            self._create_normalBom(prodId, processedIds)
        self.message_post(body=_('Created Normal Bom.'))
        return False

    def _jump_document_wf(self,
                          documentBrws,
                          check_state):
        """
        this function is here in order to customize the document workflow
        :documentBrws     <ir_attachment>
        :check_in_check   bool shuld I move also the document
        :return: True will jump the workflow for the current document / False will performe the workflow
        """
        return False

    def checkWorkflow(self,
                      docInError,
                      linkeddocuments,
                      check_state,
                      check_in_check=True):
        docIDs = []
        attachment = self.env['ir.attachment']
        for documentBrws in linkeddocuments:
            if documentBrws.engineering_state in check_state:
                if check_in_check and documentBrws.is_checkout:
                    if check_in_check:
                        logging.info(f"{documentBrws.name} workflow jump for custom rule check_in_check")
                    else:
                        docInError.append(_(f"Document {documentBrws.name} : {documentBrws.engineering_revision} is checked out by user {documentBrws.checkout_user}") )
                    continue
                if self._jump_document_wf(documentBrws,check_state):
                    continue
                docIDs.append(documentBrws.id)
                if documentBrws.is3D():
                    doc_layout_ids = documentBrws.getRelatedLyTree(documentBrws.id)
                    docIDs.extend(self.checkWorkflow(docInError,
                                                     attachment.browse(doc_layout_ids),
                                                     check_state,
                                                     check_in_check=check_in_check))
                    raw_doc_ids = documentBrws.getRelatedRfTree(documentBrws.id, recursion=True)
                    docIDs.extend(self.checkWorkflow(docInError,
                                                     attachment.browse(raw_doc_ids),
                                                     check_state,
                                                     check_in_check=check_in_check))
        return list(set(docIDs))

    def _action_ondocuments(self,
                            action_name,
                            include_statuses=[],
                            check_in_check=True):
        """
            move workflow on documents having the same state of component
        """
        docIDs = []
        docInError = []
        for oldObject in self:
            if action_name != 'reject' and action_name != 'release':
                check_state = oldObject.engineering_state
            else:
                check_state = CONFIRMED_STATUS
            docIDs.extend(self.checkWorkflow(docInError,
                                             oldObject.linkeddocuments,
                                             include_statuses+[check_state],
                                             check_in_check=check_in_check))
        if docInError:
            msg = _("Error on workflow operation")
            for e in list(set(docInError)):
                msg = msg + "\n" + e
            msg = msg + _("\n\nCheck-In All the document in order to proceed !!")
            raise UserError(msg)
        self.moveDocumentWorkflow(docIDs, action_name)

    def moveDocumentWorkflow(self, docIDs, status):
        ir_attachment = self.env['ir.attachment']
        if len(docIDs) > 0:
            ir_attachment_ids = ir_attachment.browse(docIDs)
            if status == CONFIRMED_STATUS:
                ir_attachment_ids.action_confirm()
            elif status == START_STATUS:
                ir_attachment_ids.action_draft()
            elif status == 'reject':
                ir_attachment_ids.action_draft()
            elif status == RELEASED_STATUS:
                ir_attachment_ids.action_release()
            elif status == UNDER_MODIFY_STATUS:
                ir_attachment_ids.action_cancel()
            elif status == 'suspend':
                ir_attachment_ids.action_suspend()
            elif status == 'reactivate':
                ir_attachment_ids.action_reactivate()
            elif status == OBSOLATED_STATUS:
                ir_attachment_ids.action_obsolete()
            else:
                self.customMoveDocumentWorkflow(ir_attachment_ids, status)
        return docIDs


    def customMoveDocumentWorkflow(self,
                                   ir_attachment_ids,
                                   status):
        """
        Customization use this function for further customizations on product workflow
        :ir_attachment_ids [<ir_attachment>]
        :status str state to move to
        REMARK:
            the current status is on the self object and on the attachment ids
        """
        return

    @api.model
    def _iswritable(self, oid):
        checkState = (START_STATUS,)
        if not oid.engineering_writable:
            logging.warning("_iswritable : Part (%r - %d) is not writable." % (oid.engineering_code, oid.engineering_revision))
            return False
        if oid.engineering_state not in checkState:
            logging.warning("_iswritable : Part (%r - %d) is in status %r." % (oid.engineering_code, oid.engineering_revision, oid.engineering_state))
            return False
        if not oid.engineering_code:
            logging.warning("_iswritable : Part (%r - %d) is without Engineering P/N." % (oid.name, oid.engineering_revision))
            return False
        return True

    def unlinkCheckFirstLevel(self):
        for product in self:
            if product.linkeddocuments:
                raise UserError('Cannot unlink a product containing related documents')
            if product.bom_ids:
                raise UserError('Cannot unlink a product containing BOMs')



    def unlinkRestorePreviousComponent(self):
        ctx = self.env.context.copy()
        for checkObj in self:
            prod_ids = self.search([('engineering_code', '=', checkObj.engineering_code), ('engineering_revision', '=', checkObj.engineering_revision - 1)], limit=1)
            for oldObject in prod_ids:
                oldObject.message_post(body=_('Removed : Latest Revision.'))
                ctx['check'] = False
                values = {'engineering_state': RELEASED_STATUS}
                if not oldObject.with_context(ctx).write(values):
                    msg = 'Unlink : Unable to update state in product Engineering Code = %r   Engineering Revision = %r   Document Id = %r' % (oldObject.engineering_code, oldObject.engineering_revision, oldObject.id)
                    logging.warning(msg)
                    raise UserError(_('Cannot restore previous product Engineering Code = %r   Engineering Revision = %r   Document Id = %r' % (oldObject.engineering_code, oldObject.engineering_revision, oldObject.id)))
        return True

    def unlink(self):
        for checkObj in self:
            checkObj.unlinkCheckFirstLevel()
            checkObj.linkeddocuments.unlinkCheckDocumentRelations()
            checkObj.product_tmpl_id.unlinkCheckBomRelations()
            checkObj.unlinkRestorePreviousComponent()
        return super(ProductProduct, self).unlink()



    @api.model
    def _getbyrevision(self, name, revision):
        return self.search([('engineering_code', '=', name),
                            ('engineering_revision', '=', revision)])

    def action_draft(self):
        """
            release the object
        """
        for product_product_id in self:
            product_product_id.commonWFAction(START_STATUS, [CONFIRMED_STATUS])
        return True

    def action_confirm(self):
        """
            action to be executed for Draft state
        """
        for product_product_id in self:
            product_product_id.commonWFAction(CONFIRMED_STATUS, [START_STATUS], recursive=True)
        return True

    def action_release(self):
        for product_product_id in self:
            product_product_id.commonWFAction(RELEASED_STATUS,
                                              [CONFIRMED_STATUS],
                                              recursive=True)
        return True

    def action_obsolete(self):
        """
            obsolete the object
        """
        for product_product_id in self:
            status = OBSOLATED_STATUS
            include_statuses = [RELEASED_STATUS]
            product_product_id.commonWFAction(status,
                                              include_statuses,
                                              recursive=False)
        return True

    def action_reactivate(self):
        """
            reactivate the object
        """
        for product_product_id in self:
            product_product_id.commonWFAction(RELEASED_STATUS,
                                              [OBSOLATED_STATUS])
        return True

    def commonWFAction(self,
                       status,
                       include_statuses=[],
                       recursive=False,
                       check_in_check=True):
        performed_ids=[]
        def _commonWFAction(obj,
                            status,
                            include_statuses=[],
                            recursive=False,
                            check_in_check=True):
            for product_product_id in obj:
                #
                # ansure no recursion loop
                #
                if product_product_id.id in performed_ids:
                    continue
                performed_ids.append(product_product_id.id)
                #
                # start recursion release action
                #
                if recursive:
                    errors, product_ids = product_product_id._get_recursive_parts(include_statuses)
                    if len(errors) > 0:
                        raise UserError(errors)
                    for child_product_id in product_ids:
                        _commonWFAction(child_product_id,
                                        status,
                                        include_statuses,
                                        recursive,
                                        check_in_check=check_in_check)
                product_product_id._action_ondocuments(status,
                                                       include_statuses,
                                                       check_in_check=check_in_check)
                product_product_id.product_tmpl_id.move_to_state(status)
            return True
        return _commonWFAction(self, status, include_statuses, recursive,check_in_check=check_in_check)

#  ######################################################################################################################################33
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

    @api.model
    def variant_fields_to_keep(self):
        return [
            'name',
            'tmp_material',
            'tmp_surface',
            'tmp_treatment',
            'weight',
            'uom_id',
            'std_umc1',
            'std_umc2',
            'std_umc3',
            'std_value1',
            'std_value2',
            'std_value3',
            'engineering_surface',
            'engineering_treatment',
            'type',
            'categ_id',
            'sale_ok',
            'purchase_ok',
            'route_ids',
            'linkeddocuments',
            'std_description',
            'default_code'
            ]

    @api.model
    def checkSetupDueToVariants(self, vals):
        tmplt_id = vals.get('product_tmpl_id')
        attribute_value_ids = vals.get('attribute_value_ids')
        if tmplt_id and attribute_value_ids:
            outVals = {}
            tmplBrws = self.env['product.template'].browse(tmplt_id)
            for variant in tmplBrws.product_variant_ids:
                outVals = variant.read(self.variant_fields_to_keep())[0]
                linkeddocs = outVals.get('linkeddocuments', [])
                self.checkVariantLinkeddocs(linkeddocs)
                del outVals['id']
                for key, val in outVals.items():
                    if isinstance(val, (list)):  # many2many
                        outVals[key] = [[6, 0, val]]
                    if isinstance(val, (tuple)): # many2one
                        outVals[key] = val[0]
                break
            outVals.update(vals)
            vals = outVals
        return vals

    @api.model
    def checkVariantLinkeddocs(self, doc_ids):
        for doc in self.env['ir.attachment'].browse(doc_ids):
            if not doc.ischecked_in():
                raise UserError(_('Document %r with revision %r is in check-out, cannot create variant.' % (doc.name, doc.engineering_revision)))

    @api.model_create_multi
    def create(self, vals):
        to_write=[]
        for vals_dict in vals:
            vals_dict = vals_dict.copy()
            copy_context = self.env.context.get('copy_context')
            if copy_context:
                vals_dict.update(copy_context)
            eng_code = vals_dict.get('engineering_code')
            name = vals_dict.get('name')
            if not name and eng_code:
                vals_dict['name'] = eng_code

            eng_rev = vals_dict.get('engineering_revision', 0)
            eng_code = vals_dict.get('engineering_code')
            if eng_code:
                prodBrwsList = self.search_count([('engineering_code', '=', eng_code),
                                                  ('engineering_revision', '=', eng_rev)
                                                  ])
                if prodBrwsList:
                    raise UserError('Component %r already exists' % (vals_dict['engineering_code']))
            vals_dict['is_engcode_editable'] = False
            vals_dict.update(self.checkMany2oneClient(vals_dict))
            vals_dict = self.checkSetupDueToVariants(vals_dict)
            vals_dict = self.plm_sanitize(vals_dict)
            to_write.append(vals_dict)
        try:
            res = super().create(to_write)
            return res
        except Exception as ex:
            if isinstance(ex, UserError):
                raise ex
            import psycopg2
            if isinstance(ex, psycopg2.IntegrityError):
                msg = _('Error during component creation with values:\n')
                for key, value in vals.items():
                    msg = msg + '%r = %r\n' % (key, value)
                try:
                    msg = msg + str(ex.message) + '\n'
                except:
                    pass
                msg = msg + '\n\n------------------------------\n\n' + str(ex)
                raise Exception(msg)
            logging.error("(%s). It has tried to create with values : (%s)." % (str(ex), str(vals)))
            raise Exception(_(" (%r). It has tried to create with values : (%r).") % (ex, vals))

    def write(self, vals):
        for product in self:
            if 'is_engcode_editable' not in vals and product.engineering_code not in ['-',False]:
                vals['is_engcode_editable'] = False
            vals.update(product.checkMany2oneClient(vals))
            vals = product.plm_sanitize(vals)
            if not product.description or ('description' in vals and not vals['description']):
                vals['description'] = '.'
        res =  super(ProductProduct, self).write(vals)
        ctx = self.env.context.copy()
        skip = ctx.get('skip_write_overload', False)
        if not skip:
            for product in self:
                ctx['skip_write_overload'] = True
                product.with_context(ctx).on_change_tmpmater()
                product.with_context(ctx).on_change_tmpsurface()
                product.with_context(ctx).on_change_tmptreatment()
        for product_id in self:
            if product_id._origin.id:
                product_id.checkFromOdooPlm()
        return res

    def read(self, fields=[], load='_classic_read'):
        try:
            if self.env.context.get('odooPLM'):
                if not fields:
                    fields = list(self._fields.keys())
                cleaned_up_fields = []
                for field_name, field_attrs in self.fields_get(fields).items():
                    if field_attrs['type']=='properties':
                        continue
                    cleaned_up_fields.append(field_name)
                customFields = [field.replace('plm_m2o_', '') for field in cleaned_up_fields if field.startswith('plm_m2o_')]
                fields.extend(customFields)
                fields = list(set(cleaned_up_fields))
                fields = self.plm_sanitize(fields)
                res = super(ProductProduct, self).read(fields=fields, load=load)
                return self.readMany2oneFields(res, fields)
            return super(ProductProduct, self).read(fields=fields, load=load)
        except Exception as ex:
            if isinstance(ex, AccessError) and 'sale.report' in ex.name:
                return """
Your user does not have enough permissions to make this operation. Error: \n
%r\n
Please try to contact OmniaSolutions to solve this error, or install Plm Sale Fix module to solve the problem.""" % (ex)
            raise ex

    def fieldsToKeep(self, to_write=[]):
        for vals in self.read(to_write):
            return vals
        return {}

    def readMany2oneFields(self, readVals, fields):
        return self._readMany2oneFields(self.env['product.product'], readVals, fields)

    @api.model
    def _readMany2oneFields(self, obj, readVals, fields):
        out = []
        for vals in readVals:
            fields_def = obj.fields_get(vals.keys())
            tmpVals = vals.copy()
            for fieldName, fieldVal in vals.items():
                customField = 'plm_m2o_' + fieldName
                if customField in fields:
                    logging.info('Reading many2one field %r, fieldVal %r' % (customField, fieldVal))
                    field_def = fields_def.get(fieldName)
                    if field_def.get('type', '') == 'many2one':
                        relation = field_def.get('relation', '')
                        tmpVals[customField] = ''
                        if relation:
                            if isinstance(fieldVal, int):
                                tmpVals[customField] = self.env[relation].browse(fieldVal).name
                            elif isinstance(fieldVal, (list, tuple)):
                                tmpVals[customField] = fieldVal[1]
                            else:
                                tmpVals[customField] = ''
            out.append(tmpVals)
        return out

    def checkFromOdooPlm(self):
        new_revision = self.env.context.get('new_revision', False)
        if self.env.context.get('odooPLM', False) and not new_revision:
            for product_product_id in self:
                if not product_product_id.engineering_code:
                    raise UserError("Missing engineering code for plm data")
        return True

    def checkMany2oneClient(self, vals, force_create=False):
        return self._checkMany2oneClient(self.env['product.product'], vals, force_create)

    @api.model
    def _checkMany2oneClient(self, obj, vals, force_create=False):
        out = {}
        customFields = [field.replace('plm_m2o_', '') for field in vals.keys() if field.startswith('plm_m2o_')]
        if customFields:
            fieldsGet = obj.fields_get(customFields)
            for fieldName, fieldDefinition in fieldsGet.items():
                field_id = False
                try:
                    field_id = vals.get(fieldName, False)
                except Exception as ex:
                    logging.warning('Cannot get m2o field value due to error %r' % (ex))
                if not field_id:
                    refId = self.customFieldConvert(fieldDefinition, vals, fieldName, force_create=force_create)
                    out[fieldName] = False
                    if refId:
                        out[fieldName] = refId.id
        return out

    def customFieldConvert(self, fieldDefinition, vals, fieldName, force_create=False):
        refId = False
        fieldType = fieldDefinition.get('type', '')
        referredModel = fieldDefinition.get('relation', '')
        oldFieldName = 'plm_m2o_' + fieldName
        cadVal = vals.get(oldFieldName, '')
        if fieldType == 'many2one':
            try:
                for refId in self.env[referredModel].search([('name', '=', cadVal)]):
                    return refId
                if force_create and cadVal:
                    if referredModel in ['product.product', 'product.template']:
                        return False    # With False value field is not set
                    tmp_vals = {
                        'name': cadVal
                    }
                    refId = self.sudo().env[referredModel].create(tmp_vals)
            except Exception as ex:
                logging.warning(ex)
        return refId

    @api.model
    def translateForClient(self, values=[], forcedLang=''):
        """
            Get values attribute in this format:
            values = [{'field1':value1,'field2':value2,...}]     only one element in the list!!!
            and return computed values due to language
            Get also forcedLang attribute in this format:
            forcedLang = 'en_US'
            if is not set it takes language from user
        """
        language = forcedLang
        if not forcedLang:
            resDict = self.env['res.users'].read(['lang'])
            language = resDict.get('lang', '')
        if values:
            values = values[0]
        if language and values:
            toRead = [x for x in list(values.values()) if type(x) in [str] and x]     # Where computed only string and not null string values (for performance improvement)
            toRead = list(set(toRead))                                                      # Remove duplicates
            for fieldName, valueToTranslate in list(values.items()):
                if valueToTranslate not in toRead:
                    continue
                translationObj = self.env['ir.translation']
                translationBrwsList = translationObj.search([('lang', '=', language),
                                                             ('src', '=', valueToTranslate)])
                if translationBrwsList:
                    readDict = translationBrwsList[0].read(['value'])
                    values[fieldName] = readDict.get('value', '')
        return values

    @api.model
    def get_all_translation(self, object_id, fields):
        return self.product_tmpl_id.get_all_translation(object_id, fields)

    def action_rev_docs(self):
        """
            This function is called by the button on component view, section LinkedDocuments
            Clicking that button all documents related to all revisions of this component are opened in a tree view
        """
        docIds = []
        for compBrws in self:
            engineering_code = compBrws.engineering_code
            if not engineering_code:
                logging.warning("Part %s doesn't have and engineering code!" % (compBrws.name))
                docIds.extend(compBrws.linkeddocuments.ids)
            else:
                compBrwsList = self.search([('engineering_code', '=', engineering_code)])
                for compBrws in compBrwsList:
                    docIds.extend(compBrws.linkeddocuments.ids)
        return {'domain': [('id', 'in', docIds)],
                'name': _('Related documents'),
                'view_type': 'form',
                'view_mode': 'list,form',
                'res_model': 'ir.attachment',
                'type': 'ir.actions.act_window',
                }

    def action_view_mos(self):
        tmplBrws = self.product_tmpl_id
        if tmplBrws:
            return tmplBrws.action_view_mos()
        logging.warning('[action_view_mos] product with id %s does not have a related template' % (self.id))

    def NewRevision(self):
        """
            create a new revision of current component
        """
        newComponentId = False
        engineering_revision = 0
        ctx = self.env.context.copy()
        for tmpObject in self:
            latestIDs = self.GetLatestIds([(tmpObject.engineering_code, tmpObject.engineering_revision, False)])
            for product_product_id in self.browse(latestIDs[-1]):
                product_product_id = product_product_id.sudo()
                product_product_id.engineering_state = 'undermodify'
                product_product_id.engineering_writable =  False
                product_product_id.product_tmpl_id.engineering_state = 'undermodify'
                product_product_id.product_tmpl_id.engineering_writable =  False
                engineering_revision = int(product_product_id.engineering_revision) + 1
                available_status = self._fields.get('engineering_state')._description_selection(self.env)
                dict_status = dict(available_status)
                status_lable = dict_status.get(product_product_id.engineering_state, '')
                product_product_id.message_post(body=_('Status moved to: %s by %s.' % (status_lable, self.env.user.name)))
                # store updated infos in "revision" object
                defaults = {}
                defaults['name'] = product_product_id.name          # copy function needs an explicit name value
                defaults['engineering_code'] = product_product_id.engineering_code
                defaults['engineering_revision'] = engineering_revision
                defaults['engineering_writable'] = True
                defaults['engineering_state'] = START_STATUS
                defaults['linkeddocuments'] = []                  # Clean attached documents for new revision object
                ctx['new_revision'] = True
                new_tmpl_id = product_product_id.product_tmpl_id.with_context(ctx).copy(defaults)
                new_tmpl_id._create_variant_ids()
                newCompBrws = new_tmpl_id.product_variant_id
                defaults['engineering_revision_user'] = self.env.uid
                defaults['engineering_revision_date'] = datetime.now()
                defaults['engineering_release_user'] = False
                defaults['engineering_release_date'] = False
                defaults['engineering_workflow_user'] = False
                defaults['engineering_workflow_date'] = False
                defaults['product_tmpl_id']=new_tmpl_id.id
                newCompBrws.write(defaults)
                product_product_id.message_post(body=_('Created : New Revision.'))
                newComponentId = newCompBrws.id
                break
            break
        return (newComponentId, engineering_revision)

    @api.model
    def wf_message_post_client(self, args):
        """
            args = [objId, objMessage]
        """
        objId, objMessage = args
        self.browse(objId).message_post(body=objMessage)
        return True

    @api.model
    def getBomRowCad(self, bomLineBrowse):
        """
        give back the lines
        """
        ctx = self.env.context.copy()
        ctx['lang'] = 'en_GB'
        return [bomLineBrowse.itemnum,
                emptyStringIfFalse(bomLineBrowse.product_id.name),
                bomLineBrowse.product_id.with_context(ctx).name,
                bomLineBrowse.product_id.engineering_code,
                bomLineBrowse.product_qty]

    @api.model
    def getNormalBomStd(self):
        """
            get the normal bom from the given name and revision
            RELPOS,
            $G{COMPDES="-"} / $G{COMPDES_L2="-"},
            $G{COMPNAME:f("#clear(<undef>@)")},
            $G{RELQTY},
        """
        componentName = self.env.context.get('componentName', '')
        componentRev = self.env.context.get('componentRev', 0)
        bomType = 'normal'
        logging.info('getNormalBom for compoent: %s, componentRev: %s' % (componentName, componentRev))
        out = []
        searchFilter = [('engineering_code', '=', componentName),
                        ('engineering_revision', '=', componentRev)]
        compBrwsList = self.search(searchFilter)
        for objBrowse in compBrwsList:
            for bomBrowse in objBrowse.bom_ids:
                if str(bomBrowse.type).lower() == bomType:
                    for bomLineBrowse in bomBrowse.bom_line_ids:
                        out.append(self.getBomRowCad(bomLineBrowse))
        return out

    @api.model
    def _getChildrenBomWithDocuments(self, component, level=0, currlevel=0):
        """
            Return a flat list of each child, listed once, in a Bom ( level = 0 one level only, level = 1 all levels)
        """
        result = []
        bufferdata = []
        if level == 0 and currlevel > 1:
            return bufferdata
        for bomid in component.product_tmpl_id.bom_ids:  # TODO: Bom type??
            for bomline in bomid.bom_line_ids:
                levelDict = {}
                prodBrws = bomline.product_id
                levelDict['root_props'] = prodBrws.getComponentInfos()
                levelDict['documents'] = self.computeLikedDocuments(prodBrws)
                levelDict['bom'] = self._getChildrenBom(bomline.product_id, level, currlevel + 1)
                bufferdata.append(levelDict)
            break
        result.extend(bufferdata)
        return list(set(result))

    def computeLikedDocuments(self, prodBrws):
        docList = []
        compInfos = prodBrws.getComponentInfos()
        for docBrws in prodBrws.linkeddocuments:
            docList.append({'component': compInfos, 'document': docBrws.getDocumentInfos()})
        return docList

    def getComponentInfos(self):
        return {'engineering_code': self.engineering_code or '',
                'engineering_revision': self.engineering_revision,
                'description': self.name or '',
                'desc_modify': self.desc_modify or '',    # To be created
                'name': self.name,
                '_id': self.id,
                'can_revise': self.canBeRevised(),
                }

    @api.model
    def getCloneRevisionStructure(self, values=[]):
        """
            out = {
                'root_props': {},
                'documents': [],
                'bom': [
                    {
                    'documents': [],
                    'bom': []
                    },
                ]
                }
        """
        def computeBomAllLevels(prodBrws):
            return prodBrws._getChildrenBomWithDocuments(prodBrws, level=1)

        def computeBomOneLevel(prodBrws):
            return prodBrws._getChildrenBomWithDocuments(prodBrws, level=0)

        if not values:
            return {}
        componentDict = values[0]
        computeType = values[1]  # Possible values = 'no-bom' / 'bom-all-levels' / 'bom-one-level'
        eng_code = componentDict.get('engineering_code', '')
        eng_rev = componentDict.get('engineering_revision', None)
        if not eng_code:
            logging.warning('No engineering code passed by the client %r' % (componentDict))
            return {}
        if eng_rev is None:
            logging.warning('No engineering revision passed by the client %r' % (componentDict))
            return {}
        componentId = componentDict.get('_id', None)
        if not componentId:
            prodBrws = self.search([('engineering_code', '=', eng_code),
                                    ('engineering_revision', '=', eng_rev)])
        else:
            prodBrws = self.browse(componentId)
        if not prodBrws:
            logging.warning('No component found for arguments %r' % (componentDict))
            return {}
        if computeType == 'no-bom':
            rootProps = prodBrws.getComponentInfos()
            rootProps['can_revise'] = True   # Because cames from previous new revision. So it can be revised
            return {
                'root_props': rootProps,
                'documents': self.computeLikedDocuments(prodBrws),
                'bom': []}
        elif computeType == 'bom-all-levels':
            return computeBomAllLevels(prodBrws)
        elif computeType == 'bom-one-level':
            return computeBomOneLevel(prodBrws)
        else:
            logging.warning('Unable to find computation type %r' % (componentDict))
            return {}
        return {}

    def canBeRevised(self):
        for compBrws in self:
            if compBrws.engineering_state == RELEASED_STATUS:
                return True
        return False

    @api.model
    def reviseCompAndDoc(self, elementsToClone):
        docEnv = self.env['ir.attachment']
        updatedJsonNode = elementsToClone[0]
        updatedNode = json.loads(updatedJsonNode)
        hostName, hostPws = elementsToClone[1], elementsToClone[2]
        _oldRootCompVals, _oldRootDocVals = elementsToClone[3]

        def updateDocAttrs(node, datasName):
            node['DOCUMENT_ATTRIBUTES']['OLD_FILE_NAME'] = datasName
            node['DOCUMENT_ATTRIBUTES']['CHECK_OUT_BY_ME'] = True

        def cleanRootUnCheckedComponent(compBrws, node):
            # User made and edit parts in the client but he unchecked the component in the interface
            # So I need to delete it, restore previous revision and revise only the document
            compBrws.unlink()
            return restorePreviousComponentRevision(node)

        def cleanRootUnCheckedDocument(docBrws, node):
            # User made and edit document in the client but he unchecked the component in the interface
            # So I need to delete it and restore previous revision
            docBrws.unlink()
            return restorePreviousDocumentRevision(node)

        def restorePreviousDocumentRevision(node):
            node['DOCUMENT_ATTRIBUTES']['engineering_revision'] = node['DOCUMENT_ATTRIBUTES']['engineering_revision'] - 1
            return docEnv.getDocumentBrws(node['DOCUMENT_ATTRIBUTES'])  # Try to restore previous revision (case of only document revision)

        def restorePreviousComponentRevision(node):
            node['PRODUCT_ATTRIBUTES']['engineering_revision'] = node['PRODUCT_ATTRIBUTES']['engineering_revision'] - 1
            return self.getCompBrws(node['PRODUCT_ATTRIBUTES'])  # Try to restore previous revision (case of only document revision)

        def updateCompDescModify(newCompBrwse, node):
            newCompBrwse.desc_modify = node['PRODUCT_ATTRIBUTES'].get('desc_modify', '')

        def updateDocDescModify(newDocBrws, node):
            newDocBrws.desc_modify = node['DOCUMENT_ATTRIBUTES'].get('desc_modify', '')

        def updateDocNodeByBrws(node, newDocBrws):
            node['DOCUMENT_ATTRIBUTES'].update(newDocBrws.getDocumentInfos())

        def updateCompNodeByBrws(node, newCompBrwse):
            node['PRODUCT_ATTRIBUTES'].update(newCompBrwse.getComponentInfos())

        def updateRootDocument(docBrws, node):
            if docBrws:
                newDocBrws = docBrws
                updateDocAttrs(node, docBrws.name)
                docBrws.checkout(hostName, hostPws)
                newDocBrws.desc_modify = node['DOCUMENT_ATTRIBUTES'].get('desc_modify', '')
                return newDocBrws
            return False

        def reviseCompObj(compBrws, node):
            # Raw component because BOM is not managed
            newCompId, _newCompRev = compBrws.NewRevision()
            newCompBrwse = self.browse(newCompId)
            updateCompDescModify(newCompBrwse, node)
            updateCompNodeByBrws(node, newCompBrwse)
            return newCompBrwse

        def reviseDocObj(docBrws, node):
            newDocId, _newDocIndex = docBrws.NewRevision()
            newDocBrws = docEnv.browse(newDocId)
            updateDocDescModify(newDocBrws, node)
            updateDocNodeByBrws(node, newDocBrws)
            updateDocAttrs(node, docBrws.name)
            newDocBrws.checkout(hostName, hostPws)
            return newDocBrws

        def reviseComp(node, isRoot, compBrws, docBrws, reviseDocument, reviseComponent):
            newCompBrwse = False
            newDocBrws = False
            deleted = False
            if not reviseComponent:
                if compBrws and isRoot:
                    compBrws = cleanRootUnCheckedComponent(compBrws, node)
                else:
                    compBrws = restorePreviousComponentRevision(node)
                deleted = True
            if not deleted:
                if isRoot:
                    newCompBrwse = compBrws
                    updateCompDescModify(newCompBrwse, node)
                else:
                    newCompBrwse = reviseCompObj(compBrws, node)
            if reviseDocument:
                newDocBrws = reviseDocObj(docBrws, node)
            return newCompBrwse, newDocBrws

        def reviseDoc(node, reviseDocument, docBrws, isRoot):
            newDocBrws = False
            if not reviseDocument:
                if docBrws and isRoot:
                    cleanRootUnCheckedDocument(docBrws, node)
                else:
                    restorePreviousDocumentRevision(node)
                return False
            if isRoot:
                newDocBrws = updateRootDocument(docBrws, node)
            else:
                newDocBrws = reviseDocObj(docBrws, node)
            return newDocBrws

        def setupRelations(newDocBrws, newCompBrwse):
            if newDocBrws:
                newDocBrws.write({'linkedcomponents': [(5, 0, 0)]})  # Clean copied links
                if newCompBrwse:
                    newCompBrwse.write({'linkeddocuments': [(4, newDocBrws.id, False)]})  # Add link to component

        def nodeResursionUpdate(node, isRoot=False):
            newDocBrws = False
            newCompBrwse = False
            reviseComponent = node.get('COMPONENT_CHECKED', False)
            reviseDocument = node.get('DOCUMENT_CHECKED', False)
            compProps = node.get('PRODUCT_ATTRIBUTES', {})
            docProps = node.get('DOCUMENT_ATTRIBUTES', {})
            engCode = compProps.get('engineering_code', '')
            docName = docProps.get('name', '')
            docId = docProps.get('_id', None)
            docBrws = self.getDocBrws(docId, docProps)
            compBrws = self.getCompBrws(compProps)
            if engCode:
                newCompBrwse, newDocBrws = reviseComp(node, isRoot, compBrws, docBrws, reviseDocument, reviseComponent)
            elif docName:
                newDocBrws = reviseDoc(node, reviseDocument, docBrws, isRoot)
            setupRelations(newDocBrws, newCompBrwse)
            for childNode in node.get('RELATIONS', []):
                if childNode.get('DOCUMENT_ATTRIBUTES', {}).get('DOC_TYPE').upper() == '2D':
                    childNode['PRODUCT_ATTRIBUTES'] = {'engineering_code': ''}    # Setup the correct parent component
                nodeResursionUpdate(childNode)

        nodeResursionUpdate(updatedNode, True)
        return json.dumps(updatedNode)

    def getDocBrws(self, docId, docProps):
        docEnv = self.env['ir.attachment']
        oldDocBrws = False
        if docId:
            oldDocBrws = docEnv.browse(docId)
        else:
            oldDocBrws = docEnv.getDocumentBrws(docProps)
        return oldDocBrws

    def getCompBrws(self, compProps):
        compId = compProps.get('_id', None)
        compBrws = False
        if compId:
            compBrws = self.browse(compId)
        else:
            compBrws = self.getComponentBrws(compProps)
        return compBrws

    @api.model
    def cloneCompAndDoc(self, elementsToClone):
        docEnv = self.env['ir.attachment']
        updatedJsonNode = elementsToClone[0]
        updatedNode = json.loads(updatedJsonNode)
        hostName, hostPws = elementsToClone[1], elementsToClone[2]
        _oldRootCompVals, oldRootDocVals = elementsToClone[3]
        newRootCompProps = updatedNode.get('PRODUCT_ATTRIBUTES')
        newRootDocProps = updatedNode.get('DOCUMENT_ATTRIBUTES')

        def cleanRootDocument(oldDocBrws, node):
            oldDocBrws.unlink()
            cleanDocumentAttrs(node)

        def cleanDocumentAttrs(node):
            node['DOCUMENT_ATTRIBUTES'] = {}

        def cleanRootComponent(compBrws, node):
            # User made and edit parts in the client but he unchecked the component in the interface
            # So I need to delete it and clone only the document
            compBrws.unlink()
            cleanEngCode(node)

        def cleanEngCode(node):
            node['PRODUCT_ATTRIBUTES'] = {'engineering_code': ''}

        def createClonedRawComponent(engCode, compBrws, node):
            newBaseName = engCode + '_raw'
            newCode = docEnv.GetNextDocumentName(newBaseName)
            default = {'name': newCode,
                       'engineering_code': newCode}
            newRawComponent = compBrws.copy(default)
            node['PRODUCT_ATTRIBUTES'] = newRawComponent.getComponentInfos()
            return newCode, newRawComponent

        def cloneDocumentObj(oldDocBrws, engCode, node):
            newDocBrws = False
            if oldDocBrws.id:
                _filename, file_extension = os.path.splitext(oldDocBrws.name)
                newDocBrws = self.getNewDoc(oldDocBrws, engCode, file_extension)
                newDocBrws.checkout(hostName, hostPws)
                node['DOCUMENT_ATTRIBUTES'] = newDocBrws.getDocumentInfos()
                node['DOCUMENT_ATTRIBUTES']['OLD_FILE_NAME'] = oldDocBrws.name
                node['DOCUMENT_ATTRIBUTES']['CHECK_OUT_BY_ME'] = oldDocBrws._is_checkedout_for_me()
            return newDocBrws

        def setupRootDocument(clonedDocBrws, node):
            # oldRootDocVals are starting document properties
            # clonedDocBrws is cloned document browse
            rootOldDocBrws = docEnv.getDocumentBrws(oldRootDocVals)
            _filename, file_extension = os.path.splitext(rootOldDocBrws.name)
            clonedDocBrws.name = '%s%s' % (clonedDocBrws.name, file_extension)
            node['DOCUMENT_ATTRIBUTES']['name'] = clonedDocBrws.name
            node['DOCUMENT_ATTRIBUTES']['CHECK_OUT_BY_ME'] = True
            node['DOCUMENT_ATTRIBUTES']['OLD_FILE_NAME'] = rootOldDocBrws.name
            clonedDocBrws.checkout(hostName, hostPws)
            return clonedDocBrws

        def cloneWithComp(cloneComponent, cloneDocument, rootEngCode, oldDocBrws, compBrws, node, isRoot=False):
            newDocBrws = False
            newRawComponent = False
            if not cloneComponent:
                if compBrws and isRoot:  # Only root component has to be deleted
                    cleanRootComponent(compBrws, node)
                else:
                    cleanEngCode(node)
            else:   # Root case --> already cloned in the CAD otherwise ir a raw component
                if not isRoot:  # Part-Part case because BOM is not managed
                    rootEngCode, newRawComponent = createClonedRawComponent(rootEngCode, compBrws, node)
            if cloneDocument:
                newDocBrws = cloneDocumentObj(oldDocBrws, rootEngCode, node)
            else:
                node['DOCUMENT_ATTRIBUTES'] = {}
            return newDocBrws, newRawComponent

        def cloneWithDoc(cloneDocument, oldDocBrws, node, isRoot, baseName):
            newDocBrws = False
            if not cloneDocument:
                if oldDocBrws and isRoot:
                    cleanRootDocument(oldDocBrws, node)
                else:
                    cleanDocumentAttrs(node)
                return newDocBrws
            if isRoot:
                newDocBrws = setupRootDocument(oldDocBrws, node)
            else:
                newDocBrws = cloneDocumentObj(oldDocBrws, baseName, node)
            return newDocBrws

        def cleanAndSetupRelations(newDocBrws, compBrws):
            if newDocBrws:
                newDocBrws.write({'linkedcomponents': [(5, 0, 0)]})  # Clean copied links
                if compBrws:
                    compBrws.write({'linkeddocuments': [(4, newDocBrws.id, False)]})  # Add link to component

        def nodeResursionUpdate(node, isRoot=False):
            cloneDocument = node.get('DOCUMENT_CHECKED', False)
            compProps = node.get('PRODUCT_ATTRIBUTES', {})
            docProps = node.get('DOCUMENT_ATTRIBUTES', {})
            rootEngCode = newRootCompProps.get('engineering_code', '')
            docName = docProps.get('name', '')
            docId = docProps.get('_id', None)
            newDocBrws = False
            oldDocBrws = self.getDocBrws(docId, docProps)
            compBrws = self.getCompBrws(compProps)
            if compProps.get('engineering_code', ''):    # Node is a component-document node
                newDocBrws, newRawComponent = cloneWithComp(node.get('COMPONENT_CHECKED', False),
                                                            cloneDocument,
                                                            rootEngCode,
                                                            oldDocBrws,
                                                            compBrws,
                                                            node,
                                                            isRoot)
                compBrws = newRawComponent
            elif docName:    # Node is a document node
                baseName = docName
                engineering_code = newRootDocProps.get('engineering_code', '')
                if rootEngCode or engineering_code:
                    baseName = rootEngCode or engineering_code
                newDocBrws = cloneWithDoc(cloneDocument,
                                          oldDocBrws,
                                          node,
                                          isRoot,
                                          baseName)
            cleanAndSetupRelations(newDocBrws, compBrws)
            for childNode in node.get('RELATIONS', []):
                if childNode.get('DOCUMENT_ATTRIBUTES', {}).get('DOC_TYPE').upper() == '2D':
                    childNode['PRODUCT_ATTRIBUTES'] = {'engineering_code': ''}
                nodeResursionUpdate(childNode)

        nodeResursionUpdate(updatedNode, True)
        return json.dumps(updatedNode)

    def getNewDoc(self, oldDocBrws, startingComputeName, file_extension):
        docEnv = self.env['ir.attachment']
        newDocName = docEnv.GetNextDocumentName(startingComputeName)
        docDefaultVals = {
            'engineering_revision': 0,
            'engineering_code': newDocName,
            'name': '%s%s' % (newDocName, file_extension),
            'checkout_user': self.env.uid}
        newDocVals = oldDocBrws.Clone(docDefaultVals)
        newDocId = newDocVals.get('_id')
        newDocBrws = docEnv.browse(newDocId)
        return newDocBrws

    @api.model
    def getUuid(self):
        param = self.env['ir.config_parameter'].sudo()
        return param.get_param('database.uuid')

    def getComponentBrws(self, componentVals):
        engCode = componentVals.get('engineering_code', '')
        engRev = componentVals.get('engineering_revision', None)
        if not engCode or engRev is None:
            return self.browse()
        return self.search([
            ('engineering_code', '=', engCode),
            ('engineering_revision', '=', engRev)])

    def open_related_revisions(self):
        product_product_ids = self.search([('engineering_code', '=', self.engineering_code)])
        return {'name': _('Products'),
                'res_model': 'product.product',
                'view_type': 'form',
                'view_mode': 'list,form',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', product_product_ids.ids)],
                'context': {}}

    def open_template(self):
        return {'name': _('Products'),
                'res_model': 'product.template',
                'view_type': 'form',
                'view_mode': 'list,form',
                'type': 'ir.actions.act_window',
                'domain': [('id', '=', self.product_tmpl_id.id)],
                'context': {}}

    @api.model
    def createFromProps(self, productAttribute):
        out_product_produc_id = self.env['product.product']
        found = False
        sanitaized_attributes = {}
        for attribute_name in self._fields.keys():
            if attribute_name in productAttribute:
                sanitaized_attributes[attribute_name] = productAttribute[attribute_name]
            elif "plm_m2o_" + attribute_name in productAttribute:
                value = productAttribute["plm_m2o_" + attribute_name]
                sanitaized_attributes[attribute_name] = self.env['product.template'].translate_plm_m2o_name([self.env['product.template'],
                                                                                                            self.env['product.product']], attribute_name, value)
        language_attrs = {}
        for key in list(filter(lambda x: '@-@-@' in x,list(productAttribute.keys()))):
            field_name, language = key.split('@-@-@')
            if language not in language_attrs:
                language_attrs[language] = {field_name: productAttribute[key]}
            else:
                language_attrs[language][field_name] = productAttribute[key]

        engineering_name = sanitaized_attributes.get('engineering_code', False)
        if not engineering_name:
            return False
        if 'name' in sanitaized_attributes:
            if not sanitaized_attributes['name']:
                sanitaized_attributes['name'] = engineering_name
        for product_produc_id in self.search([('engineering_code', '=', engineering_name),
                                              ('engineering_revision', '=', sanitaized_attributes.get('engineering_revision', '0'))]):
            out_product_produc_id = product_produc_id
            found = True
            break
        if found:  # Write
            if product_produc_id.engineering_state not in [RELEASED_STATUS, OBSOLATED_STATUS]:
                out_product_produc_id.write(sanitaized_attributes)
        else:  # write
            out_product_produc_id = self.create(sanitaized_attributes)
        for lang, translated_values in language_attrs.items():
            out_product_produc_id.with_context(lang=lang).write(translated_values)
        return out_product_produc_id



    def name_get(self):
        result = []
        ret = super(ProductProduct, self).name_get()
        for res in ret:
            prod_id, eng_code = res
            prod = self.browse(prod_id)
            if prod.default_code:
                result.append(res)
                continue
            elif prod.engineering_code:
                eng_code = '[%s_%s] %s' % (prod.engineering_code, prod.engineering_revision, eng_code)
            result.append((prod.id, eng_code))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        engineering_code_products = self.search([('engineering_code', 'ilike', name)])
        product_ids = list(super(ProductProduct, self)._name_search(name,
                                                                    domain,
                                                                    operator,
                                                                    limit,
                                                                    order=None))
        return list(set(product_ids + engineering_code_products.ids))

    @api.model
    def getExpodedBom(self, ids):
        """
        function used in the client to retrieve the exploded bom
        """
        mrp_bom = self.env['mrp.bom']
        out = []
        #
        header = {'engineering_code': _('Code'),
                  'engineering_revision':_('Revision'),
                  'name':_('Description'),
                  'qty':_('Quantity'),
                  'source_name':_('Rel.Source')
                  }
        #
        def getProductData(product_tmpl_id):
            return {
                'id': product_tmpl_id.id,
                'engineering_code': product_tmpl_id.engineering_code,
                'engineering_revision': product_tmpl_id.engineering_revision,
                'name': product_tmpl_id.name,
                }
        #
        def getBomLineData(mrpBomLine):
            return {
                'qty':  mrpBomLine.product_qty,
                'source_name': mrpBomLine.source_id.name
                }
        #
        def getDictData(mrpBomLine):
            out = getProductData(mrpBomLine.product_id.product_tmpl_id)
            out.update(getBomLineData(mrpBomLine))
            return out
        #
        # ({},[({}, []),]
        #
        product_computed = []
        def computeChildLevel(product_tmpl_id):
            children = []
            if product_tmpl_id.id not in product_computed:
                product_computed.append(product_tmpl_id.id)
                mrp_bom_id = mrp_bom._get_bom(product_tmpl_id.id)
                for mrp_bom_line_id in mrp_bom_id.bom_line_ids:
                    children.append((getDictData(mrp_bom_line_id),
                                     computeChildLevel(mrp_bom_line_id.product_id.product_tmpl_id)))
            return children
        #
        for product_id in self.browse(ids):
            product_tmpl_id = product_id.product_tmpl_id
            out.append((getProductData(product_tmpl_id), computeChildLevel(product_tmpl_id)))
        #
        return (header, out)

    def get_product_bom_flat_ids(self, bom_type='normal'):
        """
        get the product browser flat list
        """
        self.ensure_one()
        out = []
        #
        def populate(product_id):
            if product_id in out:
                return
            out.append(product_id)
            for bom_id in product_id.product_tmpl_id.bom_ids.filtered(lambda x:x.type==bom_type):
                for line_id in bom_id.bom_line_ids:
                    populate(line_id.product_id)
        #
        populate(self)
        return out


    @api.model
    def get_all_document_source_path(self, attributes, *k, **kw):
        out_src = []
        #
        def fillUpSrvPath(p_p_id):
            for ir_attachment_id in p_p_id.linkeddocuments.filtered(lambda x:x.document_type=='3d'):
                is_brake=False
                for sub_ir_attachment_id in ir_attachment_id.GetRelatedDocs(getBrowse=True):
                    if sub_ir_attachment_id.document_type=='2d':
                        is_brake=True
                        break
                if is_brake:
                    continue
                out_src.append((ir_attachment_id.first_source_path,
                                ir_attachment_id.id))
        #
        product_product_id = attributes.get('_id')
        brw_product_product_id = self.browse(product_product_id)
        for product_id in brw_product_product_id.get_product_bom_flat_ids():
            fillUpSrvPath(product_id)
        return list(set(out_src))

    def action_open_linked_field(self, related_field):
        view_id = self.env["ir.model.data"]._xmlid_to_res_id("plm.document_kanban_view")
        related_field_value = getattr(self, related_field, False)
        if related_field_value:
            related_ids = related_field_value.ids
        else:
            related_ids = []
        ctx = self.env.context.copy()
        domain = [('is_plm', '=', True), ('id', 'in', related_ids)]
        ctx.update({
            "create": False,
            "delete": False,
            'default_res_ids': related_ids,
            'readonly': True
        })

        return {
            "name": "Linked Documents",
            "type": "ir.actions.act_window",
            "view_mode": "kanban",
            'domain': domain,
            "res_model": "ir.attachment",
            "target": "new",
            "views": [[view_id, "kanban"]],
            "context": ctx,
        }


class PlmTemporayMessage(models.TransientModel):
    _name = "plm.temporary.message"
    _description = "Temporary Class"
    name = fields.Text(_('Bom Result'), readonly=True)


class ProductProductDashboard(models.Model):
    _name = "report.plmcomponent"
    _description = "Report Component"
    _auto = False
    count_component_draft = fields.Integer(_('Draft'),
                                           readonly=True,
                                           translate=True)
    count_component_confirmed = fields.Integer(_('Confirmed'),
                                               readonly=True,
                                               translate=True)
    count_component_released = fields.Integer(_('Released'),
                                              readonly=True,
                                              translate=True)
    count_component_modified = fields.Integer(_('Under Modify'),
                                              readonly=True,
                                              translate=True)
    count_component_obsoleted = fields.Integer(_('Obsoleted'),
                                               readonly=True,
                                               translate=True)

    @api.model
    def init(self):
        cr = self.env.cr
        tools.drop_view_if_exists(cr, 'report_plm_component')
        cr.execute("""
            CREATE OR REPLACE VIEW report_plmcomponent AS (
                SELECT
                    (SELECT min(id) FROM product_template where engineering_code<>'') as id,
                    (SELECT count(*) FROM product_template WHERE engineering_state = 'draft' and  engineering_code<>'') AS count_component_draft,
                    (SELECT count(*) FROM product_template WHERE engineering_state = 'confirmed' and  engineering_code<>'') AS count_component_confirmed,
                    (SELECT count(*) FROM product_template WHERE engineering_state = 'released' and  engineering_code<>'') AS count_component_released,
                    (SELECT count(*) FROM product_template WHERE engineering_state = 'undermodify' and  engineering_code<>'') AS count_component_modified,
                    (SELECT count(*) FROM product_template WHERE engineering_state = 'obsoleted' and  engineering_code<>'') AS count_component_obsoleted
             )
        """)

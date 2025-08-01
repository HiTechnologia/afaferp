import logging
from odoo import _
from odoo import api
from odoo import models
from odoo import fields


class PlmDocumentRelations(models.Model):
    _name = 'ir.attachment.relation'
    _description = "Relation between document used for cad file structure"

    parent_preview = fields.Binary(related="parent_id.preview",
                                   string=_("Parent Preview"),
                                   store=False)
    parent_state = fields.Selection(related="parent_id.engineering_state",
                                    string=_("Parent Status"),
                                    store=False)
    parent_revision = fields.Integer(related="parent_id.engineering_revision",
                                     string=_("Parent Revision"),
                                     store=False)
    parent_linked = fields.Boolean(related="parent_id.is_linkedcomponents",
                                    string=_("Parent Linked Components"),
                                    store=False)
    parent_type = fields.Selection(related="parent_id.document_type",
                                    string=_("Parent Document Type"),
                                    store=False)
    child_preview = fields.Binary(related="child_id.preview",
                                  string=_("Child Preview"),
                                  store=False)
    child_state = fields.Selection(related="child_id.engineering_state",
                                   string=_("Child Status"),
                                   store=False)
    child_revision = fields.Integer(related="child_id.engineering_revision",
                                    string=_("Child Revision"),
                                    store=False)
    child_linked = fields.Boolean(related="child_id.is_linkedcomponents",
                                    string=_("Child Linked Components"),
                                    store=False)
    child_type = fields.Selection(related="child_id.document_type",
                                    string=_("Child Document Type"),
                                    store=False)
    parent_id = fields.Many2one('ir.attachment',
                                _('Related parent document'),
                                ondelete='cascade',
                                index=True,)
    child_id = fields.Many2one('ir.attachment',
                               _('Related child document'),
                               ondelete='cascade',
                               index=True)
    configuration = fields.Char(_('Configuration Name'),
                                size=1024,
                                index=True)
    link_kind = fields.Char(_('Kind of Link'),      # LyTree | HiTree | RfTree | PkgTree
                            default='HiTree',
                            size=64,
                            required=True)
    create_date = fields.Datetime(_('Date Created'),
                                  readonly=True)
    #  TODO: To remove userid field for version 10
    userid = fields.Many2one('res.users',
                             _('CheckOut User'),
                             default=False,
                             readonly=True)
    notes = fields.Char(string="Notes: ")
    preview_related = fields.Image(compute="_compute_preview_related",
                                   store=True, attachment=False,
                                   max_height=1920, max_width=1920,
                                   string=_("Child Parent Preview"))

    _sql_constraints = [
    ('relation_uniq', 'unique (parent_id,child_id,link_kind)', _('The Document Relation must be unique !')),
    ('parent_child_check', 'CHECK (parent_id <> child_id)', _('Parent child product must be different !'))
    ]

    @api.depends('parent_id.preview', 'link_kind', 'child_id')
    def _compute_preview_related(self):
        for rec in self:
            if not rec.child_preview and rec.child_id and rec.link_kind == 'ExtraTree' and rec.parent_id.preview:
                rec.preview_related = rec.parent_id.preview
                rec.child_id.preview_related = rec.parent_id.preview
            else:
                rec.preview_related = rec.preview_related

    def copy(self, default=None):
        if not default:
            default = {}
        default['parent_id'] = False
        default['child_id'] = False
        return super(PlmDocumentRelations, self).copy(default)

    def name_get(self):
        result = []
        for r in self:
            child_name = ''
            parent_name = ''
            if r.parent_id:
                if r.parent_id.engineering_code:
                    parent_name = r.parent_id.engineering_code[:8]
                else:
                    parent_name = r.parent_id.name[:8]
            if r.child_id:
                if r.child_id.engineering_code:
                    child_name = r.child_id.engineering_code[:8]
                elif r.child_id:
                    child_name = r.child_id.name[:8]
            name = "%s .. %s.." % (parent_name, child_name)
            result.append((r.id, name))
        return result

    @api.model
    def SaveStructure(self, relations, level=0, currlevel=0):
        """
            Save Document relations
        """
        def cleanStructure(relations):
            res = {}
            cleanIds = []
            for relation in relations:
                res['parent_id'], res['child_id'], res['configuration'], res['link_kind'] = relation
                link = [('link_kind', '=', res['link_kind'])]
                if (res['link_kind'] == 'LyTree') or (res['link_kind'] == 'RfTree'):
                    criteria = [('child_id', '=', res['child_id'])]
                else:
                    criteria = [('parent_id', '=', res['parent_id']), ('child_id', '=', res['child_id'])]
                cleanIds.extend(self.search(criteria + link).ids)
            self.browse(list(set(cleanIds))).unlink()

        def saveChild(relation):
            """
                save the relation
            """
            try:
                res = {}
                res['parent_id'], res['child_id'], res['configuration'], res['link_kind'] = relation
                if (res['parent_id'] is not None) and (res['child_id'] is not None):
                    if (len(str(res['parent_id'])) > 0) and (len(str(res['child_id'])) > 0):
                        if not((res['parent_id'], res['child_id']) in savedItems):
                            savedItems.append((res['parent_id'], res['child_id']))
                            self.create(res)
                else:
                    logging.error("saveChild : Unable to create a relation between documents. One of documents involved doesn't exist. Arguments(" + str(relation) + ") ")
                    raise Exception(_("saveChild: Unable to create a relation between documents. One of documents involved doesn't exist."))
            except Exception as ex:
                logging.error("saveChild : Unable to create a relation. Arguments (%s) Exception (%s)" % (str(relation), str(ex)))
                raise Exception(_("saveChild: Unable to create a relation."))

        savedItems = []
        if len(relations) < 1:  # no relation to save
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

    @api.model
    def saveDocumentRelationNew(self, parent_ir_attachment_id, child_ir_attachment_id, link_kind='HiTree'):
        if not parent_ir_attachment_id or not child_ir_attachment_id:
            return False
        if self.search_count([('parent_id', '=', parent_ir_attachment_id),
                              ('child_id', '=', child_ir_attachment_id),
                              ('link_kind', '=', link_kind)]):
            return True
        self.create({'parent_id': parent_ir_attachment_id,
                     'child_id': child_ir_attachment_id,
                    'link_kind': link_kind})
        return True

    @api.model
    def removeChildRelation(self, parent_ir_attachment_id, linkType='HiTree'):
        self.search([('parent_id', '=', parent_ir_attachment_id),
                     ('link_kind', '=', linkType)]).unlink()

    def is_2d_ok(self, from_ir_attachment_id):
        for relation_id in self.search(["|",('parent_id','=',from_ir_attachment_id.id),
                                            ('child_id','=',from_ir_attachment_id.id),
                                            ('link_kind', '=', 'LyTree')
                                        ]):
            if relation_id.parent_id.document_type=='2d' and relation_id.child_id.document_type in ['3d','pr']:
                if relation_id.parent_id.getLastCadSave() < relation_id.child_id.getLastCadSave():
                    return False
            if relation_id.child_id.document_type=='2d' and relation_id.parent_id.document_type in ['3d','pr'] :
                if relation_id.child_id.getLastCadSave()<relation_id.parent_id.getLastCadSave():
                    return False
        return True

    def is_pr_ok(self, from_ir_attachment_id):
        for relation_id in self.search(["|",('parent_id','=',from_ir_attachment_id.id),
                                            ('child_id','=',from_ir_attachment_id.id),
                                            ('link_kind', '=', 'LyTree')
                                        ]):
            if relation_id.parent_id.document_type=='pr' and relation_id.child_id.document_type in ['2d','3d']:
                if relation_id.parent_id.write_date < relation_id.child_id.write_date:
                    return False
            if relation_id.child_id.document_type=='pr' and relation_id.parent_id.document_type==['2d','3d']:
                if relation_id.child_id.write_date < relation_id.parent_id.write_date:
                    return False
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

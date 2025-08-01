from odoo import models
from odoo import fields
from odoo import api
import logging
from odoo import _


class PlmComponentDocumentRel(models.Model):
    _name = 'plm.component.document.rel'
    _description = "Component Document Relations"



    component_id = fields.Many2one('product.product',
                                   _('Linked Component'),
                                   required=True,
                                   #ondelete='cascade'
                                   )


    document_id = fields.Many2one('ir.attachment',
                                  _('Linked Document'),
                                  required=True,
                                  #ondelete='cascade'
                                  )


    _sql_constraints = [
        ('relation_unique',
         'unique(component_id, document_id)',
         _('ProductProduct and Irattachment relation has to be unique !')),
    ]

    @api.model
    def SaveStructure(self, relations, level=0, currlevel=0):
        """
            Save Document relations
        """
        def cleanStructure(relations):
            res = []
            for document_id, component_id in relations:
                latest = (document_id, component_id)
                if latest in res:
                    continue
                res.append(latest)
                prodProdObj = self.env['product.product']
                prodProdObj.write({'linkeddocuments': [(3, document_id, False)]})   # Clear link between component and document

        def saveChild(args):
            """
                save the relation
            """
            try:
                docId, compId = args
                if compId and docId:
                    compBrws = self.env['product.product'].browse(compId)
                    compBrws.write({'linkeddocuments': [(4, docId, False)]})    # Update with existing id
            except Exception as ex:
                logging.warning(ex)
                logging.warning("saveChild : Unable to create a link. Arguments (%s)." % (str(args)))
                raise Exception(_("saveChild: Unable to create a link."))

        if len(relations) < 1:  # no relation to save
            return False
        cleanStructure(relations)
        for relation in relations:
            saveChild(relation)
        return False

    @api.model
    def createFromIds(self, product_product_id, ir_attachment_id):
        exsist = self.search_count([('component_id', '=', product_product_id.id),
                                    ('document_id', '=', ir_attachment_id.id)])
        if not exsist:
            product_product_id.linkeddocuments = [(4, ir_attachment_id.id, False)]
        return True
    
    def create(self, vals):
        return super(PlmComponentDocumentRel, self).create(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

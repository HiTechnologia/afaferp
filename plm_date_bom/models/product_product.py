from odoo import api, models
from odoo.addons.plm.models.plm_mixin import OBSOLATED_STATUS


class ProductExtension(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    @api.model
    def updateObsoleteRecursive(self, prodBrws, presentsFlag=True):
        bomTmpl = self.env["mrp.bom"]
        struct = prodBrws.getParentBomStructure()

        def recursion(struct2, isRoot=False):
            for vals, parentsList in struct2:
                bom_id = vals.get("bom_id", False)
                if bom_id:
                    bomBrws = bomTmpl.browse(bom_id)
                    bomBrws._obsolete_compute()
                    if not isRoot:
                        bomBrws.obsolete_presents_recursive = presentsFlag
                recursion(parentsList)

        recursion(struct, isRoot=True)

    def write(self, vals):
        res = super(ProductExtension, self).write(vals)
        statePresent = vals.get("engineering_state", None)
        if statePresent == OBSOLATED_STATUS:
            # Here I force compute obsolete presents flag in all boms
            for prodTmplBrws in self:
                for prodBrws in prodTmplBrws.product_variant_ids:
                    self.updateObsoleteRecursive(prodBrws)
        return res

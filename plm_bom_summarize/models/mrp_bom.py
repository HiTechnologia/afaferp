from odoo import api, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    @api.model
    def saveRelationNew(self, clientArgs):
        new_context = self.env.context.copy()
        new_context["SUMMARIZE_BOM"] = True
        return super(MrpBom, self.with_context(new_context)).saveRelationNew(clientArgs)

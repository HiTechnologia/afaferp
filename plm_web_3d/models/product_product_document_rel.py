from odoo import fields, models


class PlmComponentDocumentRel(models.Model):
    _inherit = "plm.component.document.rel"

    has_web3d = fields.Boolean(
        string="Has Web3d",
        related="document_id.has_web3d",
        help="Check if this document has releted 3d web document",
    )

    def show_releted_3d(self):
        for PlmCompDocRel in self:
            if PlmCompDocRel.has_web3d:
                url = PlmCompDocRel.documeent_id.get_url_for_3dWebModel()
                return {
                    "name": "Go to website 3dWebView",
                    "res_model": "ir.actions.act_url",
                    "type": "ir.actions.act_url",
                    "target": self,
                    "url": url,
                }

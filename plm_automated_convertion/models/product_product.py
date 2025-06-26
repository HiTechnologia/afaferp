from odoo import _, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def forceRecursiveConvert(self, recursive=True):
        convert_stacks = self.env["plm.convert.stack"]
        for product in self:
            document_ids = []
            for document in product.linkeddocuments:
                if recursive:
                    document_ids.extend(
                        document.getRelatedAllLevelDocumentsTree(document)
                    )
                else:
                    document_ids.append(document.id)
            convert_stacks = (
                self.env["ir.attachment"]
                .browse(list(set(document_ids)))
                .generateConvertedFiles()
            )
        return {
            "name": _("Convert Stack"),
            "res_model": "plm.convert.stack",
            "view_type": "form",
            "view_mode": "list,form",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", convert_stacks.ids)],
            "context": {},
        }

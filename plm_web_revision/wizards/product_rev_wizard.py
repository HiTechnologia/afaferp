import logging

from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductProductExtended(models.TransientModel):
    _name = "product.rev_wizard"
    _description = "Product Revision wizards"

    reviseDocument = fields.Boolean(
        _("Document Revision"), help=_("""Make new revision of the linked document ?""")
    )
    reviseEbom = fields.Boolean(
        _("Engineering Bom Revision"),
        help=_("""Make new revision of the linked Engineering BOM ?"""),
    )
    reviseNbom = fields.Boolean(
        _("Normal Bom Revision"),
        help=_("""Make new revision of the linked Normal BOM ?"""),
    )
    reviseSbom = fields.Boolean(
        _("Spare Bom Revision"),
        help=_("""Make new revision of the linked Spare BOM ?"""),
    )

    def action_create_new_revision_by_server(self):
        product_id = self.env.context.get("active_id", False)
        active_model = self.env.context.get("active_model", False)
        if product_id and active_model:
            old_product_product_id = self.env[active_model].browse(product_id)
            old_product_template_id = old_product_product_id.product_tmpl_id
            old_product_template_id.new_version()
            new_product_template_id = (
                old_product_product_id.product_tmpl_id.get_next_version()
            )

            if self.reviseDocument:
                self.revise_related_attachment(
                    old_product_template_id, new_product_template_id
                )
            if self.reviseEbom:
                self.common_bom_revision(
                    old_product_template_id, new_product_template_id, "ebom"
                )
            if self.reviseNbom:
                self.common_bom_revision(
                    old_product_template_id, new_product_template_id, "normal"
                )
            if self.reviseSbom:
                self.common_bom_revision(
                    old_product_template_id, new_product_template_id, "spbom"
                )

            new_product_id = self.env["product.product"].search(
                [("product_tmpl_id", "=", new_product_template_id.id)], limit=1
            )

            return {
                "name": _("Revised Product"),
                "view_type": "list,form",
                "view_mode": "form",
                "res_model": "product.product",
                "res_id": new_product_id.id,
                "type": "ir.actions.act_window",
            }

        else:
            logging.error(
                "[action_create_new_revision_by_server] Cannot revise because"
                " product_id is %r" % (product_id)
            )
            raise UserError(_("Current component cannot be revised!"))

    def revise_related_attachment(self, old_product_id, new_product_id):
        new_ir_attachment_ids = self.env["ir.attachment"]
        for old_ir_attachment_id in old_product_id.product_variant_id.linkeddocuments:
            try:
                old_ir_attachment_id.new_version()

                new_ir_attachment_id = old_ir_attachment_id.get_next_version()

                new_ir_attachment_ids += new_ir_attachment_id
            except Exception as ex:
                logging.warning(ex)
        new_product_id.product_variant_id.linkeddocuments = new_ir_attachment_ids

    def common_bom_revision(self, old_product_tmpl_brw, new_product_tmpl_brw, bomType):
        bomObj = self.env["mrp.bom"]
        for bomBrws in bomObj.search(
            [("product_tmpl_id", "=", old_product_tmpl_brw.id), ("type", "=", bomType)]
        ):
            newBomBrws = bomBrws.copy()
            source_id = False
            newBomBrws.product_tmpl_id = new_product_tmpl_brw
            newBomBrws.product_id = new_product_tmpl_brw.product_variant_id
            linked_documents = new_product_tmpl_brw.product_variant_id.linkeddocuments
            if linked_documents.ids:
                source_id = linked_documents.ids[0]
            for bom_line in newBomBrws.bom_line_ids:
                bom_line.sudo().write({"source_id": source_id})

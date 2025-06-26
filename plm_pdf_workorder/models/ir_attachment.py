from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    is_production_doc = fields.Boolean("Production Document")
    doc_seq = fields.Char("Doc Sequence", readonly=True, compute="_compute_doc_seq")

    def _compute_doc_seq(self):
        for attachment in self:
            products = self.env["product.product"].search(
                [("linkeddocuments", "in", attachment.id)]
            )
            if products:
                product = products[0]
                linked_attachments = product.linkeddocuments.sorted("create_date")
                attachment.doc_seq = linked_attachments.ids.index(attachment.id) + 1
            else:
                attachment.doc_seq = 0

    def action_open_report_ir_attachment_pdf(self):

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        view_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "plm_pdf_workorder.plm_pdf_show_document_attachment")

        url = f"{base_url}/web#id={self.id}&view_id={view_id}&model=ir.attachment&view_type=form"

        return {'type': 'ir.actions.act_url', 'url': url, 'target': '_blank'}

from odoo import _, api, fields, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    use_plm_docs = fields.Boolean(_("Use PLM Docs"))
    production_doc_ids = fields.Many2many("ir.attachment",
                                          compute="_compute_production_doc_ids",
                                          inverse="_set_production_doc_ids",
                                          store=True
                                          )

    def _set_production_doc_ids(self):
        for rec in self:
            for doc_id in rec.production_doc_ids:
                attachment_id = rec.bom_id.product_id.linkeddocuments.filtered(lambda attachment: attachment.id == doc_id.id)
                attachment_id = doc_id

    @api.depends("bom_id.product_id.linkeddocuments.is_production_doc", "use_plm_docs",
                 "production_doc_ids.is_production_doc")
    def _compute_production_doc_ids(self):
        for rec in self:
            if rec.use_plm_docs and rec.bom_id.product_id.linkeddocuments:
                rec.production_doc_ids = rec.bom_id.product_id.linkeddocuments.filtered(
                    lambda doc: doc.is_production_doc == True
                )
            else:
                rec.production_doc_ids = False

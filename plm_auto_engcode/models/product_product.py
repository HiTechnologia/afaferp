from odoo import _, api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.onchange("categ_id")
    def onchange_categ_id(self):
        """
        An onchange method to update the 'engineering_code'
        """
        product = self.product_tmpl_id
        if self.engineering_code_editable:
            product.engineering_code = product._getNewCode()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _getNewCode(self):
        """
        A custom method to generate the sequence for 'engineering_code'.
        """
        if self.env.context.get("odooPLM", False):
            if self.categ_id and self.categ_id.plm_code_sequence:
                if self.old_plm_code_sequence_id.id != self.categ_id.plm_code_sequence.id:
                    self.old_plm_code_sequence_id = self.categ_id.plm_code_sequence.id
                    return self.categ_id.plm_code_sequence.next_by_id()
                elif self.old_plm_code_sequence_id.id == self.categ_id.plm_code_sequence.id:
                    return self.engineering_code

            else:
                self.old_plm_code_sequence_id = False
                return self.env["ir.sequence"].next_by_code("plm.eng.code")
        return False

    engineering_code = fields.Char(
        _("Part Number"),
        index=True,
        help=_(
            "This is engineering reference to manage a different P/N from item Name."
        ),
        size=64,
    )
    old_plm_code_sequence_id = fields.Many2one('ir.sequence')

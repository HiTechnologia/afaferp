from odoo import api, models


class ProductProductExtension(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals):
        product_product_ids = super(ProductProductExtension, self).create(vals)
        for product_product_id in product_product_ids:
            product_product_id.update_name_lang(vals)
        return product_product_ids

    def write(self, vals):
        res = super(ProductProductExtension, self).write(vals)
        self.update_name_lang(vals)
        return res

    def update_name_lang(self, vals):
        update_translation = False
        for check in [
            "std_description",
            "umc1",
            "umc2",
            "umc3",
            "std_value1",
            "std_value2",
            "std_value3",
        ]:
            if check in vals:
                update_translation = True
                break
        if update_translation:
            land_trans = self.get_description_leng()
            self.update_field_translations("name", land_trans)

    def get_description_leng(self):
        out = {}
        for product_product in self:
            if not product_product.std_description:
                continue
            for code_leng in (
                self.env["res.lang"].search([("active", "=", True)]).mapped("code")
            ):
                std_description_obj_ctx = product_product.std_description.with_context(
                    lang=code_leng
                )

                description = product_product.computeDescription(
                    std_description_obj_ctx,
                    std_description_obj_ctx.umc1,
                    std_description_obj_ctx.umc2,
                    std_description_obj_ctx.umc3,
                    product_product.std_value1,
                    product_product.std_value2,
                    product_product.std_value3,
                )
                out[code_leng] = description
        return out

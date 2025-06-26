import logging
from odoo import api, models


class ProductTemplateExtension(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals):
        obj_pp = self.env["product.product"]
        for val_dict in vals:
            new_default_code = obj_pp.computeDefaultCode(val_dict)
            if new_default_code:
                logging.info("OdooPLM: Default Code set to %s " % (new_default_code))
                val_dict["default_code"] = new_default_code
        return super().create(vals)

    def write(self, vals):
        for product_template_id in self:
            new_default_code = self.env['product.product'].computeDefaultCode(vals,
                                                                              product_template_id)
            if new_default_code :
                vals['default_code'] = new_default_code
        return super(ProductTemplateExtension, self).write(vals)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

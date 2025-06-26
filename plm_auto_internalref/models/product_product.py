import logging
from odoo import models
from odoo import api


class ProductProductExtension(models.Model):
    _name = "product.product"
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals):
        for val_dict in vals:
            new_default_code = self.computeDefaultCode(val_dict)
            if new_default_code:
                logging.info("OdooPLM: Default Code set to %s " % (new_default_code))
                val_dict["default_code"] = new_default_code
        return super().create(vals)

    @property
    def getDefaultCodeTemplate(self):
        return "%s_%s"

    def computeDefaultCode(self, vals={}, objBrowse=None):
        """
        Function to be overloaded for changing the inetrnal referense computation
        :vals dict like with all the value that be updated
        :objBrowse product.product or product.template in case of write operation
        """

        out = False
        in_revision = self.env.context.get("new_revision", False)
        engineering_code = vals.get("engineering_code", "")
        engineering_revision = vals.get("engineering_revision", 0)
        default_code = vals.get("default_code")
        if objBrowse:  # suppose write operation
            if not engineering_code:
                engineering_code = objBrowse.engineering_code
            if not engineering_revision:
                engineering_revision = objBrowse.engineering_revision
            if not default_code:
                default_code = objBrowse.default_code
        if in_revision and engineering_code and engineering_code != "-":
            out = self.getDefaultCodeTemplate % (engineering_code, engineering_revision)
        if engineering_code and not default_code and engineering_code != "-":
            out = self.getDefaultCodeTemplate % (engineering_code, engineering_revision)
        if default_code == out:
            return False
        if default_code:
            out = f"{engineering_code}_{engineering_revision}"
        return out

    def write(self, vals):
        ret = False
        for product in self:
            new_default_code = product.computeDefaultCode(vals, product)
            if product.default_code!=product.computeDefaultCode(vals, product):
                logging.info("OdooPLM: Default Code set to %s " % (new_default_code))
                vals["default_code"] = new_default_code
            ret = super(models.Model, product).write(vals)
        return ret

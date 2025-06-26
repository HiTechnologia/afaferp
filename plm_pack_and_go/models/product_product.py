from odoo import models


class PlmComponent(models.Model):
    _inherit = "product.product"

    def unlink(self):
        for prodBrws in self:
            packAndGoObj = self.env["pack.and_go"]
            presentPackAndGo = packAndGoObj.search([
                ("component_id", "=", prodBrws.product_tmpl_id.id)
            ])
            presentPackAndGo.unlink()
        return super(PlmComponent, self).unlink()

from odoo import _, fields, models


class Plm_checkout_custom(models.Model):
    _inherit = "plm.checkout"

    write_uid = fields.Integer(_("Write User Id"))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

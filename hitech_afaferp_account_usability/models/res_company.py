from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # There is a native field invoice_terms which is displayed on res.config.settings
    # when the ir.config_parameter account.use_invoice_terms is True
    # But there are several problems with this native field:
    # - it is copied on the 'narration' field of account.move => we don't want that
    # - the text block is very small on the form view of res.config.settings
    # So I decided to have our own field "static_invoice_terms"
    # The native field can still be used when you need to customise some
    # terms and conditions on each invoice (not very common, but...)
    # To underline this different with the native field, I prefix it with 'static_'
    static_invoice_terms = fields.Text(
        translate=True, string="Legal Terms on Invoice")

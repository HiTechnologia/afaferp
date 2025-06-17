from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Similar to the field static_invoice_terms in account_usability_akretion
    static_sale_terms = fields.Text(
        translate=True, string="Legal Terms on Quotation")

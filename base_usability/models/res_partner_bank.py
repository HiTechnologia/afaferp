from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    # In the 'base' module, they didn't put any string, so the bank name is
    # displayed as 'Name', which the string of the related field it
    # points to
    bank_name = fields.Char(string='Bank Name')

    @api.depends('currency_id')
    def _compute_display_name(self):
        for acc in self:
            name = acc.acc_number
            if acc.currency_id:
                 name = f"{name} ({acc.currency_id.name})"
            if acc.bank_id:
                 name = f"{name} - {acc.bank_id.name}"
            acc.display_name = name

from odoo import api, fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    industry_id = fields.Many2one('res.partner.industry', string='Partner Industry', readonly=True)

    @api.model
    def _select(self):
        return SQL(
            "%s, COALESCE(partner.industry_id, commercial_partner.industry_id) AS industry_id",
            super()._select())

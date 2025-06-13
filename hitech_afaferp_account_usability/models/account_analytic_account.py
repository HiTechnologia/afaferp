from odoo import api, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.depends_context('analytic_account_show_code_only')
    def _compute_display_name(self):
        if self._context.get('analytic_account_show_code_only'):
            for rec in self:
                rec.display_name = rec.code or rec.name
        else:
            return super()._compute_display_name()

    _sql_constraints = [(
        'code_company_unique',
        'unique(code, company_id)',
        'An analytic account with the same code already '
        'exists in the same company!')]

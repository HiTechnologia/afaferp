# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountBalanceReport(models.TransientModel):
    _name = 'account.balance.report'
    _inherit = "account.common.account.report"
    _description = 'Trial Balance Report'

    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_balance_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_balance_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    name = fields.Char(string="Trial Balance", default="Trial Balance", required=True, translate=True)
    journal_ids = fields.Many2many('account.journal',
                                   'account_balance_report_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True,
                                   default=[])

    @api.model
    def _get_report_name(self):
        period_id = self._get_selected_period_id()
        return self.env['consolidation.period'].browse(period_id)['display_name'] or _("Trial Balance")

    def _print_report(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref(
            'base_accounting_kit.action_report_trial_balance').report_action(
            records, data=data)

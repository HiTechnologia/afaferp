# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPrintJournal(models.TransientModel):
    _name = "account.print.journal"
    _inherit = "account.common.journal.report"
    _description = "Account Print Journal"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_common_print_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_common_print_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    name = fields.Char(string="Journal Audit", default="Journal Audit", required=True, translate=True)
    sort_selection = fields.Selection(
        [('date', 'Date'), ('move_name', 'Journal Entry Number')],
        'Entries Sorted by', required=True, default='move_name')
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True,
                                   default=lambda self: self.env[
                                       'account.journal'].search(
                                       [('type', 'in', ['sale', 'purchase'])]))

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        return self.env.ref(
            'base_accounting_kit.action_report_journal').with_context(
            landscape=True).report_action(self, data=data)

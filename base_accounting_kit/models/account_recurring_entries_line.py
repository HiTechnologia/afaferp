# -*- coding: utf-8 -*-
from odoo import fields, models


class GetAllRecurringEntries(models.TransientModel):
    """Model for managing account recurring entries lines."""
    _name = 'account.recurring.entries.line'
    _description = 'Account Recurring Entries Line'

    date = fields.Date('Date')
    template_name = fields.Char('Name')
    amount = fields.Float('Amount')
    tmpl_id = fields.Many2one('account.recurring.payments', string='id')

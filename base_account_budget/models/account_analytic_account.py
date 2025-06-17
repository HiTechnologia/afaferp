# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountAnalyticAccount(models.Model):
    """Inherits the AccountAnalytic model to add new budget line field that
    connect with the budget line modules"""
    _inherit = "account.analytic.account"

    budget_line = fields.One2many('budget.lines',
                                  'analytic_account_id',
                                  'Budget Lines')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        return res

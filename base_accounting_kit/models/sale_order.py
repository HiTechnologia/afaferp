# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class SaleOrder(models.Model):
    """The Class inherits the sale.order model for adding the new
        fields and functions"""
    _inherit = 'sale.order'

    has_due = fields.Boolean(string='Has due')
    is_warning = fields.Boolean(string='Is warning')
    due_amount = fields.Float(string='Due Amount',
                              related='partner_id.due_amount')

    def _action_confirm(self):
        """To check the selected customers due amount is exceed than
        blocking stage"""
        if self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.blocking_stage:
                if self.partner_id.blocking_stage != 0:
                    raise UserError(_(
                        "%s is in  Blocking Stage and "
                        "has a due amount of %s %s to pay") % (
                                        self.partner_id.name, self.due_amount,
                                        self.currency_id.symbol))
        return super(SaleOrder, self)._action_confirm()

    @api.onchange('partner_id')
    def check_due(self):
        """To show the due amount and warning stage"""
        if self.partner_id and self.partner_id.due_amount > 0 \
                and self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            self.has_due = True
        else:
            self.has_due = False
        if self.partner_id and self.partner_id.active_limit\
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.warning_stage:
                if self.partner_id.warning_stage != 0:
                    self.is_warning = True
        else:
            self.is_warning = False

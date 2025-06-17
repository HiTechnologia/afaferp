# -*- coding: utf-8 -*-
from odoo import api, models


class AccountPaymentMethod(models.Model):
    """The class inherits the account payment method for supering the
    _get_payment_method_information function"""
    _inherit = "account.payment.method"

    @api.model
    def _get_payment_method_information(self):
        """Super the function to update the pdc values"""
        res = super()._get_payment_method_information()
        res['pdc'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
        return res

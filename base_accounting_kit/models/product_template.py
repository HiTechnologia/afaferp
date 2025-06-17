# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    """Inherited the model for adding new fields and functions"""
    _inherit = 'product.template'

    asset_category_id = fields.Many2one('account.asset.category',
                                        string='Asset Type',
                                        company_dependent=True,
                                        ondelete="restrict")
    deferred_revenue_category_id = fields.Many2one('account.asset.category',
                                                   string='Deferred Revenue Type',
                                                   company_dependent=True,
                                                   ondelete="restrict")

    def _get_asset_accounts(self):
        """Override method to customize asset accounts based on asset and deferred revenue categories."""
        res = super(ProductTemplate, self)._get_asset_accounts()
        if self.asset_category_id:
            res['stock_input'] = self.property_account_expense_id
        if self.deferred_revenue_category_id:
            res['stock_output'] = self.property_account_income_id
        return res

# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """Defines a model for configuration settings with additional fields for
     managing customer credit limit and Anglo-Saxon accounting settings."""
    _inherit = 'res.config.settings'

    customer_credit_limit = fields.Boolean(string="Customer Credit Limit")

    use_anglo_saxon_accounting = fields.Boolean(string="Use Anglo-Saxon accounting", readonly=False,
                                                related='company_id.anglo_saxon_accounting')

    @api.model
    def get_values(self):
        """Retrieve the values for configuration settings including the
         customer credit limit from the database parameters. """
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        customer_credit_limit = params.get_param('customer_credit_limit',
                                                 default=False)
        res.update(customer_credit_limit=customer_credit_limit)
        return res

    def set_values(self):
        """Set the customer credit limit value in the database parameters using superuser access."""
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            "customer_credit_limit",
            self.customer_credit_limit)

    @api.model
    def get_view_id(self):
        """Retrieve the ID of the view for bank reconciliation widget form."""
        view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'base_accounting_kit.view_bank_reconcile_widget_form')
        return view_id

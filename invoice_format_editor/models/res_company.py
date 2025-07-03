# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """Inheriting the res company model"""
    _inherit = 'res.company'

    base_layout = fields.Selection(
        selection=[('default', 'Default'),
                   ('modern', 'Modern'),
                   ('normal', 'Normal'),
                   ('old', 'Old Standard')],
        required=True, string="Invoice Document Layout", default="default",
        help="base layout selection")
    document_layout_id = fields.Many2one("doc.layout",
                                         string="Invoice Layout Configuration",
                                         help="Invoice layout configuration")

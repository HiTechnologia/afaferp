# -*- coding: utf-8 -*-
from odoo import fields, models


class MultipleInvoice(models.Model):
    """Multiple Invoice Model"""
    _name = "multiple.invoice"
    _description = 'Multiple Invoice'
    _order = "sequence"

    sequence = fields.Integer(string='Sequence No')
    copy_name = fields.Char(string='Invoice Copy Name')
    journal_id = fields.Many2one('account.journal', string="Journal")

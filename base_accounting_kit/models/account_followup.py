# -*- coding: utf-8 -*-
from odoo import fields, models


class Followup(models.Model):
    """Model for managing account follow-ups."""
    _name = 'account.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'

    followup_line_ids = fields.One2many('followup.line', 'followup_id',
                                        'Follow-up', copy=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    name = fields.Char(related='company_id.name', readonly=True)

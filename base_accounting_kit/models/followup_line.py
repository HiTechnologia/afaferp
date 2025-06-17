# -*- coding: utf-8 -*-
from odoo import fields, models


class FollowupLine(models.Model):
    """Model for defining follow-up criteria including the action name, sequence order, due days, and related follow-ups."""
    _name = 'followup.line'
    _description = 'Follow-up Criteria'
    _order = 'delay'

    name = fields.Char('Follow-Up Action', required=True, translate=True)
    sequence = fields.Integer(
        help="Gives the sequence order when displaying a list of follow-up lines.")
    delay = fields.Integer('Due Days', required=True,
                           help="The number of days after the due date of the invoice"
                                " to wait before sending the reminder."
                                "  Could be negative if you want to send a polite alert beforehand.")
    followup_id = fields.Many2one('account.followup', 'Follow Ups',
                                  ondelete="cascade")

from odoo import models, fields


class AccountMove(models.Model):
    """Inheriting the account move model and added the base layout model and
    a relational field to doc layout model"""
    _inherit = 'account.move'

    base_layout = fields.Selection(
        selection=[('default', 'Default'),
                   ('modern', 'Modern'),
                   ('normal', 'Normal'),
                   ('old', 'Old Standard')],
        required=True,
        string="Invoice Document Layout",
        default="default", help="The invoice document layout selection field")
    theme_id = fields.Many2one(
        'doc.layout',
        related='company_id.document_layout_id', string="Theme",
        help="The relational field for document layout")

from odoo import _, fields, models


class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    activity_user_ids = fields.Many2many('res.users',
                                         'activity_type_user_rel',
                                         'activity_type_id',
                                         'user_id',
                                         _('Template Documents'))

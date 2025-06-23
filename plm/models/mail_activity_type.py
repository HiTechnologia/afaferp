from odoo import models
from odoo import fields
from odoo import _


class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    change_activity_type = fields.Selection(selection=[('request', 'Request'),
                                                       ('plm_activity', 'Order')
                                                       ], 
                                            string='Change Activity Type')
    

from odoo import fields, models


class MailActivityChildrenRel(models.Model):
    _name = 'mail.activity.children.rel'
    _description = "Activity children relation"

    name = fields.Char('Name')
    user_id = fields.Many2one('res.users', 'User')
    activity_user_id = fields.Many2one(related='mail_children_activity_id.user_id')
    mail_children_activity_id = fields.Many2one('mail.activity', 'Child Activity')
    mail_parent_activity_id = fields.Many2one('mail.activity', 'Parent Activity')
    plm_state = fields.Selection(related='mail_children_activity_id.plm_state')

class MailActivityChildrenRel(models.TransientModel):
    _name = 'mail.activity.children.rel.shedule'
    _description = "Activity children relation shedule"

    name = fields.Char('Name')
    user_id = fields.Many2one('res.users', 'User')
    activity_user_id = fields.Many2one(related='mail_children_activity_id.activity_user_id')
    mail_children_activity_id = fields.Many2one('mail.activity.schedule', 'Child Activity')
    mail_parent_activity_id = fields.Many2one('mail.activity.schedule', 'Parent Activity')
    plm_state = fields.Selection(related='mail_children_activity_id.plm_state')

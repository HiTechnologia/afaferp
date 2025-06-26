from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def systray_get_activities(self):
        """ Update the systray icon of res.partner activities to use the
        contact application one instead of base icon. """
        activities = super(ResUsers, self).systray_get_activities()
        for activity_dict in activities:
            model = activity_dict.get('model', '')
            if model and model in ['product.product', 'product.template']:
                mail_activity_id = self.env['mail.activity']
                today = fields.Date.context_today(self)
                today_count = mail_activity_id.search_count(
                    [('res_model', '=', model), ('plm_state', '!=', 'finished'), ('user_id', '=', self.env.uid),
                     ('date_deadline', '=', today)])
                overdue_count = mail_activity_id.search_count(
                    [('res_model', '=', model), ('plm_state', '!=', 'finished'), ('user_id', '=', self.env.uid),
                     ('date_deadline', '<', today)])
                planned_count = mail_activity_id.search_count(
                    [('res_model', '=', model), ('plm_state', '!=', 'finished'), ('user_id', '=', self.env.uid),
                     ('date_deadline', '>', today)])
                activity_dict['total_count'] = today_count + overdue_count + planned_count
                activity_dict['overdue_count'] = overdue_count
                activity_dict['today_count'] = today_count
                activity_dict['planned_count'] = planned_count
        return activities

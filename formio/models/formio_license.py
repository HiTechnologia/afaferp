
import json

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.tools import format_date


class FormioLicense(models.Model):
    _name = 'formio.license'
    _description = 'Forms License'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    uuid = fields.Char(
        string='UUID',
        compute='_compute_license_fields',
        store=True
    )
    key = fields.Text('Key', required=True, tracking=True)
    valid_until_date = fields.Date(
        string='Valid Until',
        compute='_compute_license_fields',
        store=True
    )
    domains = fields.Char(
        string='Domains',
        compute='_compute_license_fields',
        store=True
    )
    active = fields.Boolean(string='Active', default=True, tracking=True)
    renewal_reminder_weeks = fields.Integer(
        default=4,
        string='Renewal Reminders Weeks Before Valid Until',
        tracking=True,
        help='The interval of weeks before the Valid Until date, when a license renewal reminder (activity) is created for the Renewal Reminder Users.'
    )
    renewal_reminder_user_ids = fields.Many2many(
        'res.users',
        string='Renewal Reminder Users',
        domain=lambda self: [('groups_id', 'in', self.env.ref('base.group_user').id)],
        required=True,
        tracking=True,
        help='Internal users who receive license renewal reminders (activities).'
    )
    generate_renewal_reminders_state = fields.Selection(
        selection=[('generate', 'Generate'), ('regenerate', 'Regenerate')],
        compute='_compute_generate_renewal_reminders_state',
        default='generate',
        store=True,
    )

    @api.depends('key')
    def _compute_license_fields(self):
        for rec in self:
            if rec.key:
                parts = self.key.split('#')
                part_dict = json.loads(parts[0])
                rec.uuid = part_dict['uuid']
                rec.valid_until_date = part_dict['validUntil']
                rec.domains = ', '.join(part_dict['domains'])

    @api.depends('renewal_reminder_weeks', 'renewal_reminder_user_ids')
    def _compute_generate_renewal_reminders_state(self):
        for rec in self:
            if rec._get_renewal_reminder_activities():
                rec.generate_renewal_reminders_state = 'regenerate'
            else:
                rec.generate_renewal_reminders_state = 'generate'

    def _compute_display_name(self):
        for rec in self:
            name = '{res_name} - {domains} - {valid_until_date}'.format(
                res_name=self._description,
                domains=rec.domains,
                valid_until_date=format_date(
                    self.env,
                    rec.valid_until_date,
                    lang_code=self._context.get('lang')
                )
            )
            rec.display_name = name

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.generate_renewal_reminder_activities()
        return res

    def _get_renewal_reminder_summary(self):
        return _('Renewal Reminder')

    def _get_renewal_reminder_note(self, user=None):
        summary = '%s - %s' % (self.display_name, self._get_renewal_reminder_summary())
        heading_details = _('License Details')
        heading_renewal = _('The license can be extended or renewed in the following ways')
        li_pay_invoice = _('Pay the Forms License subscription renewal invoice if you received the invoice.')
        li_contact = _('Contact the Forms app vendor by email or website to request a renewal or new Forms License subscription.')
        lines = [
            '<b>%s</b><br/><br/>' % summary,
            '<b>%s</b><br/>' % heading_details,
            '%s: %s<br/>' % (self._fields['uuid'].string, self.uuid),
            '%s: %s<br/>' % (self._fields['domains'].string, self.domains),
            '%s: %s<br/><br/>' % (self._fields['valid_until_date'].string, self._format_valid_until_date(user)),
            '<b>%s</b>' % heading_renewal,
            '<ul>',
            '<li>{pay_invoice}</li>'.format(pay_invoice=li_pay_invoice),
            '<li>{contact}</li>'.format(contact=li_contact),
            '</ul>',
        ]
        body = Markup('%s' % ''.join(lines))
        return body

    def _format_valid_until_date(self, user=None):
        if user:
            lang_code = user.lang
        else:
            lang_code = self._context.get('lang')
        valid_until_date = format_date(
            self.env,
            self.valid_until_date,
            lang_code=lang_code
        )
        return valid_until_date

    def generate_renewal_reminder_activities(self):
        for rec in self:
            if rec.renewal_reminder_weeks and rec.renewal_reminder_user_ids:
                unset_generate_renewal_reminders_state = False
                rec.unlink_renewal_reminder_activities()
                activity_type = self.env.ref('formio.mail_act_formio_license_renewal_reminder').sudo()
                res_model_id = self.env['ir.model'].sudo()._get_id(self._name)
                today = fields.Date.today()
                for idx in range(rec.renewal_reminder_weeks):
                    week = idx + 1
                    date_deadline = rec.valid_until_date - relativedelta(weeks=week)
                    if date_deadline >= today:
                        for user in rec.renewal_reminder_user_ids:
                            summary = rec._get_renewal_reminder_summary()
                            note = rec._get_renewal_reminder_note(user)
                            format_date_deadline = format_date(
                                self.env,
                                date_deadline,
                                lang_code=user.lang
                            )
                            vals = {
                                'summary': '%s (%s)' % (summary, format_date_deadline),
                                'note': note,
                                'activity_type_id': activity_type.id,
                                'date_deadline': date_deadline,
                                'res_id': rec.id,
                                'res_model_id': res_model_id,
                                'user_id': user.id,
                                'automated': True
                            }
                            # Note: mail.activity create(vals_list)
                            # raises unique constraint error on followers.
                            self.env['mail.activity'].create(vals)
                        unset_generate_renewal_reminders_state = True
            if unset_generate_renewal_reminders_state:
                rec.generate_renewal_reminders_state = False

    def unlink_renewal_reminder_activities(self):
        for rec in self:
            activities = rec._get_renewal_reminder_activities()
            activities.unlink()

    def _get_renewal_reminder_activities(self):
        self.ensure_one()
        try:
            # try/except to fix ValueError (below) upon module update:
            # ValueError: External ID not found in the system: formio.mail_act_formio_license_renewal_reminder
            activity_type = self.env.ref('formio.mail_act_formio_license_renewal_reminder').sudo()
            domain = [
                ('activity_type_id', '=', activity_type.id),
                ('automated', '=', True)
            ]
            return self.activity_ids.filtered_domain(domain)
        except Exception:
            return False

    @api.model
    def cron_notify_renewal_reminder_actitivies(self):
        activity_type = self.env.ref('formio.mail_act_formio_license_renewal_reminder').sudo()
        domain = [
            ('res_model', '=', 'formio.license'),
            ('activity_type_id', '=', activity_type.id),
            ('date_deadline', '<=', fields.Date.today())
        ]
        notify_activities = self.env['mail.activity'].sudo().search(domain)
        notify_activities.action_notify()

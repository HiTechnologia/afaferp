
import json
import logging
import uuid

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import AccessError, UserError

from ..utils import get_field_selection_label, json_loads

from .formio_builder import (
    STATE_DRAFT as BUILDER_STATE_DRAFT,
    STATE_CURRENT as BUILDER_STATE_CURRENT,
    STATE_OBSOLETE as BUILDER_STATE_OBSOLETE,
)

_logger = logging.getLogger(__name__)

STATE_PENDING = 'PENDING'
STATE_DRAFT = 'DRAFT'
STATE_COMPLETE = 'COMPLETE'
STATE_ERROR = 'ERROR'
STATE_CANCEL = 'CANCEL'


class Form(models.Model):
    _name = 'formio.form'
    _description = 'Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _order = 'id DESC'

    _interval_selection = {'minutes': 'Minutes', 'hours': 'Hours', 'days': 'Days'}
    _interval_types = {
        'minutes': lambda interval: relativedelta(minutes=interval),
        'hours': lambda interval: relativedelta(hours=interval),
        'days': lambda interval: relativedelta(days=interval),
    }

    builder_id = fields.Many2one(
        'formio.builder',
        string='Form Builder',
        required=True,
        ondelete='restrict',
    )
    builder_id_domain = fields.Binary(
        compute='_compute_builder_id_domain',
        store=False
    )
    name = fields.Char(related='builder_id.name', readonly=True)
    uuid = fields.Char(
        default=lambda self: self._default_uuid(), required=True, readonly=True, copy=False,
        string='UUID')
    title = fields.Char(string='Title', required=True, index=True, tracking=True)
    state = fields.Selection(
        selection=[
            (STATE_PENDING, 'Pending'),
            (STATE_DRAFT, 'Draft'),
            (STATE_ERROR, 'Error'),
            (STATE_COMPLETE, 'Completed'),
            (STATE_CANCEL, 'Canceled'),
        ],
        string='State', default=STATE_PENDING, tracking=True, index=True
    )
    display_state = fields.Char('Display State', compute='_compute_display_fields', store=False)
    kanban_group_state = fields.Selection(
        [('A', 'Pending'), ('B', 'Draft'), ('C', 'Completed'), ('D', 'Canceled')],
        compute='_compute_kanban_group_state', store=True)
    url = fields.Char(compute='_compute_url', readonly=True)
    act_window_url = fields.Char(compute='_compute_act_window_url', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', tracking=True)
    initial_res_model_id = fields.Many2one(related='builder_id.res_model_id', readonly=True, string='Resource Model #1')
    initial_res_model_name = fields.Char(related='initial_res_model_id.name', readonly=True, string='Resource Name #1')
    initial_res_model = fields.Char(related='initial_res_model_id.model', readonly=True, string='Resource Model Name #1')
    initial_res_id = fields.Integer("Record ID #1", help="Database ID of the record in res_model to which this applies")
    res_model_id = fields.Many2one('ir.model', readonly=True, string='Resource Model')
    res_model_name = fields.Char(related='res_model_id.name', readonly=True, string='Resource Name')
    res_model = fields.Char(related='res_model_id.model', readonly=True, string='Resource Model Name')
    res_id = fields.Integer("Record ID", help="Database ID of the record in res_model to which this applies")
    res_act_window_url = fields.Char(readonly=True)
    res_name = fields.Char(string='Record Name', readonly=True)
    res_partner_id = fields.Many2one('res.partner', readonly=True, string='Resource Partner')
    user_id = fields.Many2one(
        'res.users', string='Assigned user',
        index=True, tracking=True)
    assigned_partner_id = fields.Many2one('res.partner', related='user_id.partner_id', string='Assigned Partner')
    assigned_partner_name = fields.Char(related='assigned_partner_id.name', string='Assigned Partner Name')
    invitation_mail_template_id = fields.Many2one(
        'mail.template', 'Invitation Mail',
        domain=[('model', '=', 'formio.form')],
        help="This e-mail template will be sent on user assignment. Leave empty to send nothing.")
    submission_data = fields.Text('Submission Data', default=False)
    submission_user_id = fields.Many2one(
        'res.users', string='Submission User', readonly=True,
        help='User who submitted the form.')
    submission_partner_id = fields.Many2one('res.partner', related='submission_user_id.partner_id', string='Submission Partner')
    submission_partner_name = fields.Char(related='submission_partner_id.name', string='Submission Partner Name')
    submission_commercial_partner_id = fields.Many2one(
        related='submission_user_id.partner_id.commercial_partner_id',
        string='Submission Commercial Entity'
    )
    submission_date = fields.Datetime(
        string='Submission Date', readonly=True, tracking=True,
        help='Datetime when the form was last submitted.')
    submission_timezone = fields.Selection(_tz_get, string='Submission Timezone')
    sequence = fields.Integer(help="Usefull when storing and listing forms in an ordered way")
    portal = fields.Boolean("Portal (Builder)", related='builder_id.portal', readonly=True, help="Form is accessible by assigned portal user")
    portal_share = fields.Boolean("Portal")
    portal_save_draft_done_url = fields.Char(related='builder_id.portal_save_draft_done_url')
    portal_submit_done_url = fields.Char(related='builder_id.portal_submit_done_url')
    public = fields.Boolean("Public (Builder)", related='builder_id.public', readonly=True)
    public_share = fields.Boolean("Public", tracking=True, help="Share form in public? (with access expiration check).")
    public_access_rule_type = fields.Selection(string='Public Access Rule Type', related='builder_id.public_access_rule_type')
    public_access_date_from = fields.Datetime(
        string='Public Access From', tracking=True, help='Datetime from when the form is public shared until it expires.')
    public_access_interval_number = fields.Integer(tracking=True)
    public_access_interval_type = fields.Selection(list(_interval_selection.items()), tracking=True)
    public_access = fields.Boolean("Public Access", compute='_compute_access', help="The Public Access check. Computed public access by checking whether (field) Public Access From has been expired.")
    public_create = fields.Boolean("Public Created", readonly=True, help="Form was public created")
    public_save_draft_done_url = fields.Char(related='builder_id.public_save_draft_done_url')
    public_submit_done_url = fields.Char(related='builder_id.public_submit_done_url')
    show_title = fields.Boolean("Show Title")
    show_state = fields.Boolean("Show State")
    show_id = fields.Boolean("Show ID")
    show_uuid = fields.Boolean("Show UUID")
    show_user_metadata = fields.Boolean(string="Show User Metadata")
    iframe_resizer_body_margin = fields.Char(
        "iFrame Resizer bodyMargin",
        related="builder_id.iframe_resizer_body_margin",
    )
    full_width = fields.Boolean(related='builder_id.full_width')
    languages = fields.One2many('res.lang', related='builder_id.languages', string='Languages')
    allow_unlink = fields.Boolean("Allow delete", compute='_compute_access')
    allow_force_update_state = fields.Boolean("Allow force update State", compute='_compute_access')
    readonly_submission_data = fields.Boolean("Data is readonly", compute='_compute_access')
    allow_copy = fields.Boolean(
        string="Allow Copies",
        related="builder_id.form_allow_copy",
        help="Allow copying form submissions.",
    )
    copy_to_current = fields.Boolean(
        string="Copy To Current",
        related="builder_id.form_copy_to_current",
        help="When copying a form, always link it to the current version of the builder instead of the original builder.",
    )
    debug_mode = fields.Boolean(
        string="Debug Mode",
        related='builder_id.debug_mode'
    )

    @api.model
    def default_get(self, fields):
        result = super(Form, self).default_get(fields)
        # XXX Override (ORM) default value 0 (zero) for Integer field.
        result['res_id'] = False
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self._prepare_create_vals(vals)
        res = super().create(vals_list)
        return res

    def write(self, vals):
        states_not_allowed = [STATE_CANCEL, STATE_COMPLETE]
        if 'submission_data' in vals:
            # submission_data can only be provided per record !
            self.ensure_one()
            if self.state in states_not_allowed and not self.allow_force_update_state:
                msg = 'It is not allowed to update form with UUID {uuid} in state {state}'
                _logger.info(msg.format(uuid=self.uuid, state=self.state))
                raise AccessError(_(msg).format(uuid=self.uuid, state=self.state))
        res = super(Form, self).write(vals)
        # update timezone, if not provided and if changed by the partner.
        if not vals.get('submission_timezone'):
            if vals.get('partner_id') and vals.get('partner_id') != self.partner_id.id:
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                if partner.tz:
                    vals['submission_timezone'] = partner.tz
        return res

    def _prepare_create_vals(self, vals):
        builder = self._get_builder_from_id(vals.get('builder_id'))

        vals['show_title'] = builder.show_form_title
        vals['show_state'] = builder.show_form_state
        vals['show_id'] = builder.show_form_id
        vals['show_uuid'] = builder.show_form_uuid
        vals['show_user_metadata'] = builder.show_form_user_metadata

        # access
        vals['portal_share'] = builder.portal
        vals['public_share'] = builder.public
        if builder.public or self.env.user.id == self.env.ref('base.public_user').id:
            vals['public_access'] = True
            vals['public_access_date_from'] = fields.Datetime.now()

        # public_share exiration fields (store always)
        vals['public_access_interval_number'] = builder.public_access_interval_number
        vals['public_access_interval_type'] = builder.public_access_interval_type

        # resource model, id
        vals['res_model_id'] = builder.res_model_id.id

        if not vals.get('res_id') and self._context.get('active_model') != 'formio.builder':
            vals['res_id'] = self._context.get('active_id')
            vals['initial_res_id'] = vals['res_id']

            if not vals.get('res_name'):
                vals['res_name'] = builder.res_model_id.name

        # timezone (add if not provided already)
        if not vals.get('submission_timezone'):
            if vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                if partner and partner.tz:
                    vals['submission_timezone'] = partner.tz
            elif self.env.user.partner_id.tz:
                vals['submission_timezone'] = self.env.user.partner_id.tz
        return vals

    def _clear_res_fields(self):
        vals = {
            'initial_res_id': False,
            'res_model_id': False,
            'res_id': False,
            'res_act_window_url': False,
            'res_name': False,
            'res_partner_id': False
        }
        self.write(vals)

    def _prepare_partner_vals(self, submission_data, partner_vals):
        if submission_data.get(self.builder_id.component_partner_name):
            partner_vals['name'] = submission_data.get(self.builder_id.component_partner_name)
        return partner_vals

    def _get_builder_from_id(self, builder_id):
        """
        Use `sudo` in to bypass any 'Administration/Access Rights' access error.
        This is considered safe, because it's a low-level method.
        """
        return self.env["formio.builder"].sudo().browse(builder_id)

    @api.depends('uuid')
    def _compute_builder_id_domain(self):
        for rec in self:
            rec.builder_id_domain = self._get_builder_id_domain()

    def _get_builder_id_domain(self):
        self.ensure_one()
        domain = [
            '|',
            ('state', '=', BUILDER_STATE_CURRENT),
            '|',
            '&', ('state', '=', BUILDER_STATE_DRAFT), ('backend_use_draft', '=', True),
            '&', ('state', '=', BUILDER_STATE_OBSOLETE), ('backend_use_obsolete', '=', True)
        ]
        return domain

    @api.depends('state')
    def _compute_kanban_group_state(self):
        for r in self:
            if r.state == STATE_PENDING:
                r.kanban_group_state = 'A'
            if r.state == STATE_DRAFT:
                r.kanban_group_state = 'B'
            if r.state == STATE_COMPLETE:
                r.kanban_group_state = 'C'
            if r.state == STATE_CANCEL:
                r.kanban_group_state = 'D'

    def _compute_access(self):
        user_groups = self.env.user.groups_id
        for form in self:
            # allow_unlink
            if self.env.su:
                form.allow_unlink = True
            else:
                unlink_form = self.get_form(form.uuid, 'unlink')
                if unlink_form or self.env.su:
                    form.allow_unlink = True
                else:
                    form.allow_unlink = False

            # allow_state_update
            if self.env.su:
                form.allow_force_update_state = True
            elif self.env.user.has_group('formio.group_formio_admin'):
                form.allow_force_update_state = True
            elif (
                form.builder_id.allow_force_update_state_group_ids
                and (user_groups & form.builder_id.allow_force_update_state_group_ids)
            ):
                form.allow_force_update_state = True
            else:
                form.allow_force_update_state = False

            # readonly_submission_data
            if self.env.su:
                form.readonly_submission_data = False
            elif not form.id and self.env.user.has_group('formio.group_formio_admin'):
                form.readonly_submission_data = False
            elif self.env.user.has_group('formio.group_formio_form_update'):
                form.readonly_submission_data = False
            else:
                form.readonly_submission_data = True

            # public
            form.public_access = form._public_access()

    def _public_access(self):
        if self.public_share and self.public_access_date_from:
            now = fields.Datetime.now()
            interval_delta = self._interval_types[self.public_access_interval_type](
                self.public_access_interval_number
            )
            expire_on = self.public_access_date_from + interval_delta
            if self.public_access_interval_number == 0:
                return False
            elif self.public_access_date_from > now:
                return False
            else:
                return expire_on >= now
        else:
            return False

    @api.depends('state')
    def _compute_display_fields(self):
        for r in self:
            r.display_state = get_field_selection_label(r, 'state')

    def _compute_display_name(self):
        for r in self:
            r.display_name = '{title} [{id}]'.format(title=r.title, id=r.id)

    def _decode_data(self, data):
        """ Convert data (str) to dictionary

        :param str data: submission_data string
        :return str data: submission_data as dictionary
        """
        data = json_loads(data)
        return data

    def after_submit(self):
        """ Method is called everytime a form is submitted. """
        for action in self.builder_id.server_action_ids.sorted(key='sequence').filtered(
            lambda a: a.formio_form_execute_after_action in ['submit', 'submit_save_draft']
        ):
            action.with_context(active_model=self._name, active_id=self.id).run()

    def after_save_draft(self):
        """ Method is called everytime a form is save as draft. """
        for action in self.builder_id.server_action_ids.sorted(key='sequence').filtered(
            lambda a: a.formio_form_execute_after_action in ['save_draft', 'submit_save_draft']
        ):
            action.with_context(active_model=self._name, active_id=self.id).run()

    def action_view_formio(self):
        # return {
        #     "type": "ir.actions.act_url",
        #     "url": self.url,
        #     "target": "new"
        # }
        return {
            "name": self.display_name,
            "type": "ir.actions.act_window",
            "res_model": "formio.form",
            "views": [(False, 'formio_form')],
            "view_mode": "formio_form",
            "target": "current",
            "res_id": self.id,
            "context": {}
        }

    def action_draft(self):
        if not self.allow_force_update_state:
            raise UserError(_("You're not allowed to (force) update the Form into Draft state."))

        vals = {'state': STATE_DRAFT}
        submission_data = self._decode_data(self.submission_data)
        if 'submit' in submission_data:
            del submission_data['submit']
            vals['submission_data'] = json.dumps(submission_data)

        self.with_context(formio_form_action_draft=True).write(vals)

    def action_complete(self):
        if not self.allow_force_update_state:
            raise UserError(_("You're not allowed to (force) update the Form into Complete state."))
        self.write({'state': STATE_COMPLETE})

    def action_cancel(self):
        if not self.allow_force_update_state:
            raise UserError(_("You're not allowed to (force) update the Form into Cancel state."))
        self.write({'state': STATE_CANCEL})

    def action_copy(self, force_copy_to_current=False):
        if not self.allow_copy:
            raise UserError(_("You're not allowed to copy this form."))

        builder = self.builder_id
        if self.copy_to_current or force_copy_to_current:
            builder = self.env['formio.builder'].get_builder_by_name(self.builder_id.name)

        if not builder:
            raise UserError(_("There is no Form Builder available to link this form to."))

        return self.copy(default={'state': STATE_DRAFT, 'builder_id': builder.id})

    def action_copy_to_current(self):
        new_form = self.action_copy(force_copy_to_current=True)

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'formio.form',
            'target': 'current',
            'res_id': new_form.id,
        }

    def action_send_invitation_mail(self):
        compose_form_id = self.env.ref('mail.email_compose_message_wizard_form').id
        if self.portal:
            template_id = self.env.ref('formio.mail_invitation_portal_user').id
        else:
            template_id = self.env.ref('formio.mail_invitation_internal_user').id
        ctx = dict(
            default_composition_mode='comment',
            default_res_ids=self.ids,
            default_model='formio.form',
            default_use_template=bool(template_id),
            default_template_id=template_id,
            custom_layout='mail.mail_notification_light'
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def _default_uuid(self):
        return str(uuid.uuid4())

    @api.onchange('builder_id')
    def _onchange_builder(self):
        if not self.env.user.has_group('formio.group_formio_user_all_forms'):
            self.user_id = self.env.user.id
        self.title = self.builder_id.title
        self.show_title = self.builder_id.show_form_title
        self.show_state = self.builder_id.show_form_state
        self.show_id = self.builder_id.show_form_id
        self.show_uuid = self.builder_id.show_form_uuid
        self.show_user_metadata = self.builder_id.show_form_user_metadata

        # public share
        self.public_share = self.builder_id.public
        self.public_access_interval_number = self.builder_id.public_access_interval_number
        self.public_access_interval_type = self.builder_id.public_access_interval_type

        if self.builder_id.public:
            self.public_access_date_from = fields.Datetime.now()

    @api.onchange('portal')
    def _onchange_portal(self):
        res = {}
        group_portal = self.env.ref('base.group_portal').id
        group_formio_user = self.env.ref('formio.group_formio_user').id
        group_formio_user_all = self.env.ref('formio.group_formio_user_all_forms').id
        if not self.portal:
            if self.user_id.has_group('base.group_portal'):
                self.user_id = False
            res['domain'] = {
                'user_id': [
                    ('groups_id', '!=', group_portal),
                    '|',
                    ('groups_id', '=', group_formio_user),
                    ('groups_id', '=', group_formio_user_all),
                ]}
        else:
            res['domain'] = {
                'user_id': [
                    '|',
                    ('groups_id', '=', group_portal),
                    ('groups_id', '!=', False)
                ]
            }
        return res

    def _compute_url(self):
        # sudo() is needed for regular users.
        for r in self:
            url = '{base_url}/formio/form/{uuid}'.format(
                base_url=r.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                uuid=r.uuid)
            r.url = url

    def _compute_act_window_url(self):
        # sudo() is needed for regular users.
        for r in self:
            action = self.env.ref('formio.action_formio_form')
            url = '/web?#id={id}&view_type=form&model={model}&action={action}'.format(
                id=r.id,
                model=r._name,
                action=action.id)
            r.act_window_url = url

    def action_open_res_act_window(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            "views": [[False, "form"]],
        }

    @api.model
    def get_form(self, uuid, mode):
        """ Verifies access to form and return form or False. """

        form = self.sudo().search([('uuid', '=', uuid)], limit=1)
        if form:
            try:
                # Catch the deny access exception
                form.check_access(mode)
            except AccessError as e:
                _logger.info(e)
                return False

        # portal user
        if self.env.user.has_group('base.group_portal'):
            form = self.sudo().search([('uuid', '=', uuid)], limit=1)
            if not form or not form.portal_share or form.user_id.id != self.env.user.id:
                return False
        return form

    @api.model
    def get_public_form(self, uuid, public_share=False):
        """ Check access and return public form or False. """

        domain = [
            ('uuid', '=', uuid),
            ('public_share', '=', public_share)
        ]
        form = self.sudo().search(domain, limit=1)
        if form and form.public_access:
            return form
        else:
            return False

    def _get_js_options(self):
        """ formio.js (API) options """
        options = {
            'i18n': self.i18n_translations()
        }
        if self.state in [STATE_COMPLETE, STATE_CANCEL]:
            options['readOnly'] = True

            if self.builder_id.view_as_html:
                options['renderMode'] = 'html'
                options['viewAsHtml'] = True  # backwards compatible (version < 4.x)?
        return options

    def _get_js_params(self):
        """ Odoo JS (Owl component) misc. params """
        Param = self.env['ir.config_parameter'].sudo()
        cdn_base_url = Param.get_param('formio.cdn_base_url')
        params = {
            'cdn_base_url': cdn_base_url,
            'portal_save_draft_done_url': self.portal_save_draft_done_url,
            'portal_submit_done_url': self.portal_submit_done_url,
            'public_save_draft_done_url': self.public_save_draft_done_url,
            'public_submit_done_url': self.public_submit_done_url,
            'wizard_on_change_page_save_draft': self.builder_id.wizard and self.builder_id.wizard_on_change_page_save_draft,
        }
        return params

    def _etl_odoo_data(self):
        return {}

    def _generate_odoo_domain(self, domain=[], params={}):
        return self.builder_id._generate_odoo_domain(domain=domain, formio_form=self, params=params)

    def i18n_translations(self):
        i18n = self.builder_id.i18n_translations()
        return i18n

    def mail_activity_partner_linking(self, partner_email, record=False, user_id=False):
        if not user_id:
            user_id = self.builder_id.component_partner_activity_user_id
        if user_id:
            rec = record or self
            rec.activity_schedule(
                'formio.mail_act_partner_linking',
                user_id=user_id.id,
                summary=_('Link the Form to the appropriate Partner'),
                note=_('Found multiple Partners with email <strong>%s</strong> submitted in the Form.') % partner_email
            )
        else:
            _logger.error('No user configured (in settings) for mail_activity_partner_linking')

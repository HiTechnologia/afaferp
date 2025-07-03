

import logging
import os
import re
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ServerAction(models.Model):
    _inherit = "ir.actions.server"

    formio_ref = fields.Char(
        string="Forms Ref",
        compute='_compute_formio_ref',
        store=True,
        help="Identifies a server action with related form builder.",
    )
    formio_form_execute_after_action = fields.Selection(
        [
            ('submit', 'Submit'),
            ('save_draft', 'Save Draft'),
            ('submit_save_draft', 'Submit and Save Draft')
        ],
        string='Forms Execute After',
        help='If assigned in a Form Builder (Actions API), this sever action will be executed.'
    )
    formio_builder_ids = fields.Many2many(
        'formio.builder',
        compute='_compute_formio_builder_ids',
        search='_search_formio_builder_ids'
    )

    def _search_formio_builder_ids(self, operator, operand):
        domain = [('id', 'in', operand)]
        builders = self.env['formio.builder'].search(domain)
        return [('id', 'in', builders.mapped('server_action_ids').ids)]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        if active_model == 'formio.builder' and active_id:
            builder = self.env['formio.builder'].browse(active_id)
            builder.server_action_ids = [fields.Command.link(res.id)]
        return res

    @api.depends('model_id')
    def _compute_formio_ref(self):
        form_model = self.env.ref('formio.model_formio_form')
        for rec in self:
            if rec.model_id.id == form_model.id and not rec.formio_ref:
                rec.formio_ref = str(uuid.uuid4())
            elif rec.model_id.id != form_model.id:
                rec.formio_ref = False

    def _compute_formio_builder_ids(self):
        domain = [('server_action_ids', 'in', self.ids)]
        builders = self.env['formio.builder'].search(domain)
        for rec in self:
            rec.formio_builder_ids = self.env['formio.builder'].id
            for builder in builders:
                if rec.id in builder.server_action_ids.ids:
                    rec.formio_builder_ids = [fields.Command.link(builder.id)]

    @api.constrains('formio_ref')
    def constaint_check_formio_ref(self):
        for rec in self:
            if rec.formio_ref:
                if re.search(r"[^a-zA-Z0-9_-]", rec.formio_ref) is not None:
                    raise ValidationError(_('Form Ref is invalid. Use ASCII letters, digits, "-" or "_".'))

    @api.constrains('formio_ref')
    def _constraint_unique_formio_ref(self):
        for rec in self:
            domain = [("formio_ref", "=", rec.formio_ref)]
            if rec.formio_ref and self.search_count(domain) > 1:
                msg = _(
                    'A Server Action with Form Ref "%s" already exists.\nForm Ref should be unique.'
                ) % (rec.formio_ref)
                raise ValidationError(msg)

    @api.returns('self')
    def copy(self, default=None):
        default = dict(default or {})
        default["formio_ref"] = False
        new_actions = super().copy(dict(default or {}))
        for old_action, new_action in zip(self, new_action):
            if old_action.formio_ref:
                new_action.write({"formio_ref": str(uuid.uuid4())})
        return new_actions

    def _get_eval_context(self, action=None):
        eval_context = super()._get_eval_context(action)
        eval_context['logger'] = _logger
        eval_context['os_getenv'] = os.getenv
        return eval_context

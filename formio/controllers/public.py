import json
import logging

from odoo import http, fields, _
from odoo.http import request

from ..models.formio_builder import STATE_CURRENT as BUILDER_STATE_CURRENT
from ..models.formio_form import (
    STATE_DRAFT as FORM_STATE_DRAFT,
    STATE_COMPLETE as FORM_STATE_COMPLETE,
)

from .exceptions import FormioException

from .utils import (
    generate_uuid4,
    log_form_submisssion,
    update_dict_allowed_keys,
    validate_csrf,
)

_logger = logging.getLogger(__name__)


class FormioPublicController(http.Controller):

    ####################
    # Form - public uuid
    ####################

    @http.route('/formio/public/form/<string:uuid>', type='http', auth='public', website=True)
    def public_form_root(self, uuid):
        form = self._get_public_form(uuid, self._check_public_form())
        if not form:
            msg = 'Form UUID %s' % uuid
            return request.not_found(msg)
        else:
            languages = form.builder_id.languages
            lang_en = request.env.ref('base.lang_en')
            if lang_en.active and form.builder_id.language_en_enable and 'en_US' not in languages.mapped('code'):
                languages |= request.env.ref('base.lang_en')
            values = {
                'form': form,
                'form_languages': languages,
                'formio_css_assets': form.builder_id.formio_css_assets,
                'formio_js_assets': form.builder_id.formio_js_assets,
                # uuid is used to disable assets (js, css) caching by hrefs
                'uuid': generate_uuid4()
            }
            return request.render('formio.formio_form_public_embed', values)

    @http.route('/formio/public/form/<string:form_uuid>/config', type='http', auth='public', methods=['GET'],csrf=False, website=True)
    def form_config(self, form_uuid, **kwargs):
        form = self._get_public_form(form_uuid, self._check_public_form())
        res = {'schema': {}, 'options': {}, 'params': {}}

        if form and form.builder_id.schema:
            args = request.httprequest.args
            res['csrf_token'] = request.csrf_token()
            try:
                res['schema'] = json.loads(form.builder_id.schema)
                res['options'] = self._get_public_form_js_options(form)
                res['locales'] = self._get_public_form_js_locales(form.builder_id)
                res['params'] = self._get_public_form_js_params(form.builder_id)
            except Exception as e:
                formio_exception = FormioException(e, form=form)
                error_message, error_traceback = formio_exception.render_exception_load()
                res['error_message'] = error_message
                if request.session.debug and request.env.user.has_group('base.group_user'):
                    res['error_traceback'] = error_traceback
            try:
                etl_odoo_config = form.builder_id.sudo()._etl_odoo_config(
                    formio_form=form, params=args.to_dict()
                )
                res['options'].update(etl_odoo_config.get('options', {}))
            except Exception as e:
                formio_exception = FormioException(e, form=form)
                error_message, error_traceback = formio_exception.render_exception_load()
                res['error_message'] = error_message
                if request.session.debug and request.env.user.has_group('base.group_user'):
                    res['error_traceback'] = error_traceback
        return request.make_json_response(res)

    @http.route('/formio/public/form/<string:uuid>/submission', type='http', methods=['GET'], auth='public', csrf=False, website=True)
    def public_form_submission(self, uuid):
        form = self._get_public_form(uuid, self._check_public_form())

        # Submission data
        if form and form.submission_data:
            submission_data = {'submission': json.loads(form.submission_data)}
        else:
            submission_data = {'submission': {}}

        # ETL Odoo data
        if form:
            try:
                etl_odoo_data = form.sudo()._etl_odoo_data()
                submission_data['submission'].update(etl_odoo_data)
            except Exception as e:
                formio_exception = FormioException(e, form=form)
                error_message, error_traceback = formio_exception.render_exception_load()
                submission_data['error_message'] = error_message
                if request.session.debug and request.env.user.has_group('base.group_user'):
                    submission_data['error_traceback'] = error_traceback
        return request.make_json_response(submission_data)

    @http.route('/formio/public/form/<string:uuid>/submit', type='http', auth="public", methods=['POST'], csrf=False, website=True)
    def public_form_submit(self, uuid, **kwargs):
        """ POST with ID instead of uuid, to get the model object right away """
        self.validate_csrf()
        res = {}
        form = self._get_public_form(uuid, self._check_public_form())
        if not form:
            _logger.info('formio.form with UUID %s not found' % uuid)
            res = {'error_message': _('The form was not found.')}
            return request.make_json_response(res)
        post = request.get_json_data()
        vals = {
            'submission_data': json.dumps(post['data']),
            'submission_user_id': request.env.user.id,
            'submission_date': fields.Datetime.now(),
        }

        if post.get('saveDraft') or (
            post['data'].get('saveDraft') and not post['data'].get('submit')
        ):
            vals['state'] = FORM_STATE_DRAFT
        else:
            vals['state'] = FORM_STATE_COMPLETE

        try:
            form.write(vals)
            if vals.get('state') == FORM_STATE_COMPLETE:
                form.after_submit()
            elif vals.get('state') == FORM_STATE_DRAFT:
                form.after_save_draft()
            # debug mode is checked/handled
            log_form_submisssion(form)
        except Exception as e:
            formio_exception = FormioException(e, form=form)
            error_message, error_traceback = formio_exception.render_exception_submit()
            res['error_message'] = error_message
            if request.session.debug and request.env.user.has_group('base.group_user'):
                res['error_traceback'] = error_traceback
            form.write({'state': 'ERROR'})
        res.update({
            'form_uuid': uuid,
            'submission_data': form.submission_data
        })
        return request.make_json_response(res)

    ###################
    # Form - public new
    ###################

    @http.route('/formio/public/form/new/<string:builder_uuid>', type='http', auth='public', methods=['GET'], website=True)
    def public_form_new_root(self, builder_uuid):
        """ Render the formio.builder with the provided uuid. """
        formio_builder = self._get_public_builder(builder_uuid)
        if not formio_builder:
            msg = 'Form Builder UUID %s: not found' % builder_uuid
            return request.not_found(msg)
        elif not formio_builder.public:
            msg = 'Form Builder UUID %s: not public' % builder_uuid
            return request.not_found(msg)
        # elif not formio_builder.state != BUILDER_STATE_CURRENT:
        #     msg = 'Form Builder UUID %s not current/published' % builder_uuid
        #     return request.not_found(msg)
        else:
            values = {
                'builder': formio_builder,
                'public_form_new': True,
                # 'languages' already injected in rendering somehow
                'form_languages': formio_builder.languages,
                'formio_css_assets': formio_builder.formio_css_assets,
                'formio_js_assets': formio_builder.formio_js_assets,
                # uuid is used to disable assets (js, css) caching by hrefs
                'uuid': generate_uuid4()
            }
            return request.render('formio.formio_form_public_new_embed', values)

    @http.route('/formio/public/form/new/current/<string:builder_current_uuid>', type='http', auth='public', methods=['GET'], website=True)
    def public_form_new_current_uuid_root(self, builder_current_uuid, **kwargs):
        """ Render the current (state == 'CURRENT') formio.builder
        version with the provided current_uuid. """
        formio_builder = self._get_public_builder_current_uuid(builder_current_uuid)
        if not formio_builder:
            msg = 'Form Builder (public UUID) %s: not found' % builder_current_uuid
            return request.not_found(msg)
        elif not formio_builder.public:
            msg = 'Form Builder (public UUID) %s: not public' % builder_current_uuid
            return request.not_found(msg)
        # elif not formio_builder.state != BUILDER_STATE_CURRENT:
        #     msg = 'Form Builder UUID %s not current/published' % builder_uuid
        #     return request.not_found(msg)
        else:
            values = {
                'builder': formio_builder,
                'public_form_new': True,
                # 'languages' already injected in rendering somehow
                'form_languages': formio_builder.languages,
                'formio_css_assets': formio_builder.formio_css_assets,
                'formio_js_assets': formio_builder.formio_js_assets,
                # uuid is used to disable assets (js, css) caching by hrefs
                'uuid': generate_uuid4()
            }
            return request.render('formio.formio_form_public_new_embed', values)

    @http.route('/formio/public/form/new/<string:builder_uuid>/config', type='http', auth='public', methods=['GET'], csrf=False, website=True)
    def public_form_new_config(self, builder_uuid):
        formio_builder = self._get_public_builder(builder_uuid)
        res = {'schema': {}, 'options': {}}

        if not formio_builder or not formio_builder.public or formio_builder.state != BUILDER_STATE_CURRENT:
            _logger.info('formio.builder with UUID %s not found' % builder_uuid)
            res = {'error_message': _('The form was not found.')}
            return request.make_json_response(res)

        if formio_builder.schema:
            res['csrf_token'] = request.csrf_token()
            try:
                res['schema'] = json.loads(formio_builder.schema)
                res['options'] = self._get_public_new_form_js_options(formio_builder)
                res['locales'] = self._get_public_form_js_locales(formio_builder)
                res['params'] = self._get_public_form_js_params(formio_builder)
            except Exception as e:
                formio_exception = FormioException(e)
                error_message, error_traceback = formio_exception.render_exception_load()
                res['error_message'] = error_message
                if request.session.debug and request.env.user.has_group('base.group_user'):
                    res['error_traceback'] = error_traceback
        args = request.httprequest.args
        try:
            etl_odoo_config = formio_builder.sudo()._etl_odoo_config(params=args.to_dict())
            res['options'].update(etl_odoo_config.get('options', {}))
        except Exception as e:
            formio_exception = FormioException(e)
            error_message, error_traceback = formio_exception.render_exception_load()
            res['error_message'] = error_message
            if request.session.debug and request.env.user.has_group('base.group_user'):
                res['error_traceback'] = error_traceback
        return request.make_json_response(res)

    @http.route('/formio/public/form/new/<string:builder_uuid>/submission', type='http', auth='public', methods=['GET'], csrf=False, website=True)
    def public_form_new_submission(self, builder_uuid):
        formio_builder = self._get_public_builder(builder_uuid)

        if not formio_builder or not formio_builder.public:
            _logger.info('formio.builder with UUID %s not found' % builder_uuid)
            res = {'error_message': _('The form was not found.')}
            return request.make_json_response(res)

        args = request.httprequest.args
        submission_data = {}
        try:
            etl_odoo_data = formio_builder.sudo()._etl_odoo_data(params=args.to_dict())
            submission_data.update(etl_odoo_data)
        except Exception as e:
            formio_exception = FormioException(e)
            error_message, error_traceback = formio_exception.render_exception_load()
            submission_data['error_message'] = error_message
            if request.session.debug and request.env.user.has_group('base.group_user'):
                submission_data['error_traceback'] = error_traceback
        return request.make_json_response(submission_data)

    @http.route('/formio/public/form/new/<string:builder_uuid>/submit', type='http', auth="public", methods=['POST'], csrf=False, website=True)
    def public_form_new_submit(self, builder_uuid, **kwargs):
        res = {}
        self.validate_csrf()

        formio_builder = self._get_public_builder(builder_uuid)
        if not formio_builder:
            _logger.info('formio.builder with UUID %s not found' % builder_uuid)
            res['error_message'] = _('The form was not found')
            return request.make_json_response(res)

        post = request.get_json_data()
        Form = request.env['formio.form']
        vals = {
            'builder_id': formio_builder.id,
            'title': formio_builder.title,
            'public_create': True,
            'public_share': True,
            'submission_data': json.dumps(post['data']),
            'submission_date': fields.Datetime.now(),
            'submission_user_id': request.env.user.id
        }

        save_draft = post.get('saveDraft') or (
            post['data'].get('saveDraft') and not post['data'].get('submit')
        )
        if save_draft:
            vals['state'] = FORM_STATE_DRAFT
        else:
            vals['state'] = FORM_STATE_COMPLETE

        context = {'tracking_disable': True}

        try:
            if request.env.user._is_public():
                Form = Form.with_company(request.env.user.sudo().company_id)
                form = Form.with_context(**context).sudo().create(vals)
            else:
                form = Form.with_context(**context).create(vals)

            # after hooks
            if vals.get('state') == FORM_STATE_COMPLETE:
                form.after_submit()
            elif vals.get('state') == FORM_STATE_DRAFT:
                form.after_save_draft()

            request.session['formio_last_form_uuid'] = form.uuid

            # debug mode is checked/handled
            log_form_submisssion(form)

            request.session['formio_last_form_uuid'] = form.uuid
            res = {
                'form_uuid': form.uuid,
                'submission_data': form.submission_data
            }
        except Exception as e:
            formio_exception = FormioException(e, form=form)
            error_message, error_traceback = formio_exception.render_exception_submit()
            res['error_message'] = error_message
            if request.session.debug and request.env.user.has_group('base.group_user'):
                res['error_traceback'] = error_traceback
            form.write({'state': 'ERROR'})
        return request.make_json_response(res)

    #########
    # Helpers
    #########

    def _get_public_form_js_options(self, form):
        options = form._get_js_options()

        Lang = request.env['res.lang']
        # language
        if request.context.get('lang'):
            options['language'] = Lang._formio_ietf_code(request.context.get('lang'))
        elif request.env.user.lang:
            options['language'] = Lang._formio_ietf_code(request.env.user.lang)
        else:
            options['language'] = request.env.ref('base.lang_en').formio_ietf_code
        options['i18n'] = form.i18n_translations()
        return options

    def _get_public_new_form_js_options(self, builder):
        options = {
            'public_create': True,
            'embedded': True,
            'i18n': builder.i18n_translations()
        }

        # language
        Lang = request.env['res.lang']
        if request.context.get('lang'):
            options['language'] = Lang._formio_ietf_code(request.context.get('lang'))
        elif request.env.user.lang:
            options['language'] = Lang._formio_ietf_code(request.env.user.lang)
        else:
            options['language'] = request.env.ref('base.lang_en').formio_ietf_code

        return options

    def _get_public_form_js_locales(self, builder):
        return builder._get_form_js_locales()

    def _get_public_form_js_params(self, builder):
        params = builder._get_public_form_js_params()
        args = request.httprequest.args
        args_dict = args.to_dict()
        if bool(args_dict):
            params = update_dict_allowed_keys(
                params, args_dict, self._allowed_form_js_params_from_url(builder)
            )
        return params

    def _get_public_form(self, form_uuid, public_share=False):
        return request.env['formio.form'].get_public_form(form_uuid, public_share)

    def _get_public_builder(self, builder_uuid):
        return request.env['formio.builder'].get_public_builder(builder_uuid)

    def _get_public_builder_current_uuid(self, builder_current_uuid):
        return request.env['formio.builder'].get_public_builder_current_uuid(builder_current_uuid)

    def _check_public_form(self):
        return request.env.uid == request.env.ref('base.public_user').id or request.env.uid

    def _allowed_form_js_params_from_url(self, builder):
        return builder._allowed_form_js_params_from_url()

    def _get_form(self, uuid, mode):
        return request.env['formio.form'].get_form(uuid, mode)

    def validate_csrf(self):
        validate_csrf(request)

import logging
import traceback

from markupsafe import Markup
from werkzeug.exceptions import BadRequest

from odoo import http, _
from odoo.tools.misc import html_escape

_logger = logging.getLogger(__name__)


class BadCSRF(BadRequest):
    pass


class FormioException():

    def __init__(self, exception, **kwargs):
        self.exception = exception
        self.form = kwargs.get('form')

    def render_exception_load(self, **kwargs):
        message_lines = [
            _('Sorry, something went wrong while loading the form.'),
            _('Please contact us.')
        ]
        if self.form:
            message_lines.append('For reference - Form UUID: %s' % self.form.uuid)
        message = '<br/>'.join(message_lines)
        traceback_exc = traceback.format_exc()
        _logger.error(traceback_exc)
        traceback_exc_html = self._traceback_exc_html(traceback_exc)
        return message, traceback_exc_html

    def render_exception_submit(self, **kwargs):
        message_lines = [
            _('Sorry, something went wrong while processing the form.'),
            _('Please contact us.')
        ]
        if self.form:
            message_lines.append('For reference - Form UUID: %s' % self.form.uuid)
        message = '<br/>'.join(message_lines)
        traceback_exc = traceback.format_exc()
        _logger.error(traceback_exc)
        traceback_exc_html = self._traceback_exc_html(traceback_exc)
        return message, traceback_exc_html

    def _traceback_exc_html(self, traceback_exc):
        se = http.serialize_exception(self.exception)
        se['debug'] = traceback_exc
        traceback_html = [html_escape(se['debug'])]
        traceback_html = '<br/>'.join(traceback_html)
        traceback_html = traceback_html.replace('\n', '<br/>')
        traceback_html = traceback_html.replace('\\n', '<br/>')
        traceback_html = traceback_html.replace('\\\n', '<br/>')
        traceback_html = traceback_html.replace('\\\\n', '<br/>')
        return Markup(traceback_html)

import logging

from odoo import api, SUPERUSER_ID

# MODULE_UNINSTALL_FLAG = '_force_unlink'
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        field = env.ref('formio.field_formio_builder__public_uuid')
        cr.execute('UPDATE formio_builder SET public_uuid = NULL')
        tracking_values = env['mail.tracking.value'].search(
            [('field_id', '=', field.id)]
        )
        tracking_values.unlink()
        field.with_context({MODULE_UNINSTALL_FLAG: True}).unlink()
    except Exception as e:
        msg = 'Migration from %s skipped due to %s' % (version, e)
        _logger.warning(msg)

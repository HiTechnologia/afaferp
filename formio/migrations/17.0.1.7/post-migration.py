from odoo import api, SUPERUSER_ID

# MODULE_UNINSTALL_FLAG = '_force_unlink'
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    field = env.ref('formio.field_formio_builder__submission_url_add_query_params_from')
    cr.execute('UPDATE formio_builder SET submission_url_add_query_params_from = NULL')
    tracking_values = env['mail.tracking.value'].search(
        [('field_id', '=', field.id)]
    )
    tracking_values.unlink()
    field.with_context({MODULE_UNINSTALL_FLAG: True}).unlink()

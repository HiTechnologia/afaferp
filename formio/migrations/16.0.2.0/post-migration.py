from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    versions = env['formio.version'].search([])
    versions.action_add_base_translations()

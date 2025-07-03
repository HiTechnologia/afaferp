from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    domain = [('key', '=', 'formio.default_version')]
    param = env['ir.config_parameter'].search(domain)
    param.unlink()

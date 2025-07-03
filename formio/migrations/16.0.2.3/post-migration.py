from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    domain = [('public', '=', True)]
    builders = env['formio.builder'].search(domain)
    builders.write({'public_access_rule_type': 'time_interval'})

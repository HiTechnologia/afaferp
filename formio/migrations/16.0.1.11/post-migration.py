from odoo import api, registry, SUPERUSER_ID

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    vals = {'target': 'prepend'}
    env['formio.extra.asset'].search([]).write(vals)

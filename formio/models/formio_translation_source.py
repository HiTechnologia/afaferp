

from odoo import api, fields, models, _


class TranslationSource(models.Model):
    _name = 'formio.translation.source'
    _description = 'formio.js Version Translation Source'
    _rec_name = 'source'

    property = fields.Text(string='Property', required=True)
    source = fields.Text(string='Source Term', required=True)

from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class PlmFinishing(models.Model):
    _name = "plm.finishing"
    _description = "Surface Finishing"

    name = fields.Char(_('Specification'),
                       required=True,
                       translate=True)
    description = fields.Char(_('Description'),
                              size=128)
    sequence = fields.Integer(_('Sequence'),
                              help=_("Gives the sequence order when displaying a list of product categories."))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', _('Surface Finishing has to be unique !')),
    ]

    def copy(self, default=None):
        if not default:
            default = {}
        default['name'] = self.name + ' (copy)'
        return super(PlmFinishing, self).copy(default=default)

from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class PlmTreatment(models.Model):
    _name = "plm.treatment"
    _description = "Thermal Treatment"

    name = fields.Char(_('Specification'),
                       required=True,
                       translate=True)
    description = fields.Char(_('Description'),
                              size=128)
    sequence = fields.Integer(_('Sequence'),
                              help=_("Gives the sequence order when displaying a list of product categories."))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', _('Thermal Treatment has to be unique !')),
    ]
    
    def copy(self, default=None):
        if not default:
            default = {}
        default['name'] = self.name + ' (copy)'
        return super(PlmTreatment, self).copy(default=default)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

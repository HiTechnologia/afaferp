import logging
from odoo import models
from odoo import fields
from odoo import _
_logger = logging.getLogger(__name__)
# Customized Automation to standardize and normalize descriptions and characteristics.
# It will allow to insert unit of measure (or label) and values, so to allow search on parts
# and it will build standardized description and labels and values to compose part description.


class PlmDescription(models.Model):
    _name = "plm.description"
    _description = "PLM Descriptions"

    name = fields.Char(_('Note to Description'),
                       translate=True)
    description = fields.Char(_('Standard Description'),
                              default='')
    description_en = fields.Char(_('Description English'))
    umc1 = fields.Char(_('UM / Feature 1'),
                       help=_("Allow to specify a unit measure or a label for the feature."))
    fmt1 = fields.Char(_('Format Feature 1'),
                       default='',
                       help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    umc2 = fields.Char(_('UM / Feature 2'),
                       help=_("Allow to specify a unit measure or a label for the feature."))
    fmt2 = fields.Char(_('Format Feature 2'),
                       default='',
                       help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    umc3 = fields.Char(_('UM / Feature 3'),
                       help=_("Allow to specify a unit measure or a label for the feature."))
    fmt3 = fields.Char(_('Format Feature 3'),
                       default='',
                       help=_("Allow to represent the measure: %s%s allow to build um and value, %s builds only value, none builds only value."))
    fmtend = fields.Char(_('Format Feature Composed'),
                         default='',
                         help=_("Allow to represent a normalized composition of technical features : %s%s allows to build chained values."))
    unitab = fields.Char(_('Normative Rule'),
                         default='',
                         help=_("Specify normative rule (UNI, ISO, DIN...). It will be queued to build the product description."))
    sequence = fields.Integer(_('Sequence'),
                              help=_("Assign the sequence order when displaying a list of product categories."))
    show_help = fields.Boolean('Visible', default=False)

    def action_see_help(self):
        for record in self:
            record.show_help = not record.show_help



from odoo import fields, models


FORMIO_VIEW_TYPES = [
    ('formio_builder', 'formio builder'),
    ('formio_form', 'formio form')
]


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=FORMIO_VIEW_TYPES)

    def _get_view_info(self):
        return {
            'formio_builder': {'icon': 'fa fa-rocket'},
            'formio_form': {'icon': 'fa fa-rocket'}
        } | super()._get_view_info()


class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(
        selection_add=FORMIO_VIEW_TYPES,
        ondelete={'formio_builder': 'cascade', 'formio_form': 'cascade'})

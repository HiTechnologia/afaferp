import logging
from odoo.exceptions import UserError
from odoo import models
from odoo import fields
from odoo import api
from odoo import _
import logging


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    @api.returns('self')
    def search(self, args, offset=0, limit=None, order=None):
        if self.env.context.get('odooPLM'):
            self = self.sudo()
        return super(IrUiView, self).search(args, offset, limit, order)

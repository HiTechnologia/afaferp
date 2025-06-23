
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class ResUsers(models.Model):
    _inherit = 'res.users'


    def getMacros(self):
        '''
            Omnia Client Macro module make an overload of this function and enable macros
        '''
        return []

    def getCustomProcedure(self):
        '''
            Omnia CustomProcedure module make an overload of this function and enable macros
        '''
        return '', ''

    @api.model
    def koo_context_get(self):
        return dict(self.context_get())
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

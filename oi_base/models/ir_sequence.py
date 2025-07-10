
from odoo import models, api
from odoo.exceptions import UserError

class IrSequence(models.Model):
    _inherit = 'ir.sequence'
    
    @api.model
    def next_by_code(self, sequence_code, sequence_date=None):
        res = super(IrSequence, self).next_by_code(sequence_code)
        if not res:
            msg="No sequence has been found for code '%s'. Please make sure a sequence is set for %s." % (sequence_code, self.env.company.display_name)
            raise UserError(msg)
        return res
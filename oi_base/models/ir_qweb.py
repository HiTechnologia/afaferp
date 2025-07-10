
from odoo import models
from .tools import en_to_ar
import logging
_logger = logging.getLogger(__name__)

class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"
    
    def _prepare_environment(self, values):
        values.update({
            'en_to_ar' : en_to_ar,
            '_logger': _logger           
            })
        return super()._prepare_environment(values)
    
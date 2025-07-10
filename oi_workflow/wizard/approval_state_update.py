
from odoo import models, fields

class ChangeDocumentStatus(models.TransientModel):
    _name = 'approval.state.update'
    _description = 'Change Document Status'
        
    state = fields.Char(required = True, string='Status')
    res_model = fields.Char(required = True)
    res_ids = fields.Json(required = True)
    comment = fields.Html()
        
    def action_update(self):        
        records = self.env[self.res_model].browse(self.res_ids)
        if hasattr(records, "_track_set_log_message") and self.comment:
            records._track_set_log_message(self.comment)  
        records.write({"state" : self.state})
        return {'type': 'ir.actions.act_window_close'}
from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class Stage(models.Model):
    _inherit = "crm.stage"

    state = fields.Char(string="Status", required=True)

    _sql_constraints = [
        ('state_uniq', 'unique (state)', 'The status should be unique !'),
    ]    
    
    @api.model
    def _states_sync(self):
        self.env.flush_all()
        self.env.registry.clear_cache()
        to_remove_ids = self.search([])
        for idx, (state,name) in enumerate(self.env['crm.lead']._get_state()):            
            stage_id = self.search([('state','=', state)])
            if stage_id:
                to_remove_ids -= stage_id
                stage_id.sequence = idx + 1
                if stage_id.name != name:
                    stage_id.name = name
            else:
                self.env['crm.stage'].create({
                    'state' : state,
                    'name' : name,
                    'sequence' : idx + 1,
                    'fold' : state in ['lost', 'rejected']
                })                
        
        for r in to_remove_ids:
            _logger.info(f"Auto remove {r} {r.name} {r.state}")
            r.unlink()
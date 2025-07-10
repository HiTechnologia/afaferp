from . import models

from odoo.tools import SQL
from odoo.fields import apply_required, Command

import logging
_logger = logging.getLogger(__name__)

def post_init_hook(env):    
    for idx,stage_id in enumerate(env["crm.stage"].search([])):
        if idx==0:
            stage_id.state ='draft'     
            continue
        state = stage_id.name.lower()
        stage_id.state = state
        if state in ['won', 'lost', 'rejected']:            
            continue        
        approval_id = env["approval.config"].create({
            'model_id' : env['ir.model']._get_id('crm.lead'),
            'state' : state,
            'name' : stage_id.name,
            'sequence' : stage_id.sequence,
            'group_ids' : [Command.set(env.ref('sales_team.group_sale_manager').ids)],
        })
        _logger.info(f"Auto Create crm.lead approval {approval_id} {approval_id.state}")
        env["approval.buttons"].create({
            'config_id' : approval_id.id,
            'settings_id' : approval_id.setting_id.id,
            'action_type' : 'approve',
            'name' : 'Approve',
            'button_class' : 'btn-primary',
            'visible_to' : 'approval',            
        })
        env["approval.buttons"].create({
            'config_id' : approval_id.id,
            'settings_id' : approval_id.setting_id.id,
            'action_type' : 'reject',
            'name' : 'Reject',
            'button_class' : 'btn-secondary',
            'visible_to' : 'approval'
        })                
            
    env['crm.stage']._states_sync()           
    
    for stage_id in env['crm.stage'].search([]):
        env.cr.execute(SQL("UPDATE crm_lead SET state=%s WHERE stage_id=%s", stage_id.state, stage_id.id))
        
    apply_required(env['crm.stage'], 'state')
    apply_required(env['crm.lead'], 'state')
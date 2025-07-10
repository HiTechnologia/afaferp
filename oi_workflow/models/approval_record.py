from odoo import models, fields, api,tools, SUPERUSER_ID, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import config
from datetime import timedelta
from odoo.exceptions import UserError, AccessError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.addons.base.models.res_users import Users

import logging
from lxml import etree # pyright: ignore[reportAttributeAccessIssue]
import json

from inspect import getmembers
from collections import defaultdict
from markupsafe import Markup

from ..api import *

_logger = logging.getLogger(__name__)

class ApprovalRecord(models.AbstractModel):
    _name ='approval.record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Approval Record'
    _default_field_readonly = ''

    @api.model
    @tools.ormcache_context(keys=('lang',))
    def _get_state(self):
        return (self._before_approval_states_custom() or  self._before_approval_states()) + \
            self._approval_states() + \
            (self._after_approval_states_custom() or self._after_approval_states())
    
    state = fields.Selection(_get_state, string='Status', copy = False, tracking = True, required = True, group_expand=True, default = lambda self : self._get_draft_state())
    
    approval_state_id = fields.Many2one('approval.config', compute = '_calc_approval_state_id', search = '_search_approval_state_id', string='Approval Status Settings')
        
    approval_user_ids = fields.Many2many('res.users', string='Waiting Users Approval', compute = '_calc_approval_user_ids', search ='_search_approval_user_ids')    
    approval_done_user_ids = fields.Many2many('res.users', string='Completed Users Approval', compute = '_calc_approval_user_ids')    
    approval_partner_ids = fields.Many2many('res.partner', string='Waiting Partners Approval', compute = '_calc_approval_user_ids')    
    user_can_approve = fields.Boolean(compute = '_calc_approval_user_ids')
        
    document_user_id = fields.Many2one('res.users', compute = '_calc_document_user_id')    
    
    waiting_approval = fields.Boolean(compute = '_calc_waiting_approval', search= '_search_waiting_approval')
            
    log_ids = fields.Many2many('approval.log', string='Status Log', compute = '_calc_log_ids')    
        
    last_state_update = fields.Datetime(readonly = True, default = fields.Datetime.now, copy = False, string='Last Status Updated')
    workflow_states = fields.Json(compute = '_calc_workflow_states')
            
    record_cancellation_count = fields.Integer(compute='_compute_canceled_record_count', help="Counter for the canceled records related to record")
    active_record_cancellation_count = fields.Integer(compute='_compute_canceled_record_count')
    
    approval_activity_date_deadline = fields.Date(compute = "_calc_approval_activity_date_deadline", compute_sudo = True)
    
    _old_state = fields.Char(store = False, string='_old_state', compute = "_compute_old_state", inverse = "_inverse_old_state", exportable = False, export_string_translation = False)
    _approval_button_id = fields.Many2one('approval.buttons', store = False, string="_approval_button_id", compute = "_compute_approval_button_id", inverse = "_inverse_approval_button_id", exportable = False, export_string_translation = False)
    _approval_comment = fields.Char(store= False, string="_approval_comment", compute = "_compute_approval_comment", inverse = "_inverse_approval_comment", exportable = False, export_string_translation = False)
    
    duration_state_tracking = fields.Json(compute = "_calc_duration_state_tracking", string="Status Duration Tracking")
    
    approved_button_clicked = fields.Integer(store = False)

    approval_voting_ids = fields.One2many('approval.log.voting', 'record_id', string='Voting')
    approval_voting_count = fields.Integer(string='Voting Count', compute='_compute_voting_counts')
    reject_voting_count = fields.Integer(string='Reject Count', compute='_compute_voting_counts')
    vote_summary = fields.Json(string='Vote Summary', compute='_compute_vote_summary')
    vote_summary_html = fields.Html(string='Vote Summary Table', compute='_compute_vote_summary')

    approval_visible_button_ids = fields.Many2many('approval.buttons', string='Visible Buttons (by Filter Domain)', compute='_compute_visible_buttons', exportable = False, export_string_translation = False)

    @api.depends('approval_voting_ids')
    def _compute_vote_summary(self):
        for record in self:
            button_counts = defaultdict(int)
            if record.approval_voting_ids:
                for vote in record.approval_voting_ids:
                    button_counts[vote.button_id] += 1
                record.vote_summary = {button_id.name: count for button_id, count in button_counts.items()}
                record.vote_summary_html = self.env['ir.qweb']._render('oi_workflow.vote_summary_table', {'summary_data': record.vote_summary})
            else:
                record.vote_summary = {}
                record.vote_summary_html = False

    @api.depends('state')
    def _compute_visible_buttons(self):
        button_ids = self.env["approval.buttons"].sudo().search_cached([('model','=', self._name), ('active','=', True)]).filtered(lambda b: b.visible_to == "domain" and b._user_button_access())
        for record in self:
            record.approval_visible_button_ids = button_ids.filtered(lambda b: record.filtered_domain(safe_eval(b.visible_domain, {'uid': self.env.user.id})))            
    
    @api.depends('approval_voting_ids', 'approval_voting_ids.vote')
    def _compute_voting_counts(self):
        for record in self:
            record.approval_voting_count = len(record.approval_voting_ids.filtered(lambda v: v.vote == 'approve'))
            record.reject_voting_count = len(record.approval_voting_ids.filtered(lambda v: v.vote == 'reject'))
    
    def _set_approval_temp_value(self, name, value):        
        self.env.cr.precommit.data[f"approval.temp.value.{self._name}.{self.id}.{name}"] = value
        
    def _get_approval_temp_value(self, name):
        return self.env.cr.precommit.data.get(f"approval.temp.value.{self._name}.{self.id}.{name}")
        
    def _compute_old_state(self):
        for record in self:
            record._old_state = record._get_approval_temp_value('_old_state')
            
    def _inverse_old_state(self):
        for record in self:
            record._set_approval_temp_value('_old_state', record._old_state)
            
    def _compute_approval_button_id(self):
        for record in self:
            record._approval_button_id = record._get_approval_temp_value('_approval_button_id')
            
    def _inverse_approval_button_id(self):
        for record in self:
            record._set_approval_temp_value('_approval_button_id', record._approval_button_id)  
            
    def _compute_approval_comment(self):
        for record in self:
            record._approval_comment = record._get_approval_temp_value('_approval_comment')
            
    def _inverse_approval_comment(self):
        for record in self:
            record._set_approval_temp_value('_approval_comment', record._approval_comment)
    
    @api.model
    def _add_field(self, name, field):        
        if name == "state":
            for bf in field.args.get('_base_fields',()): # pyright: ignore[reportOptionalMemberAccess]
                for argname in ['args', '_args__']:
                    getattr(bf, argname, {}).pop('selection_add', None)
        return super()._add_field(name, field)    
                    
    @api.depends('state')
    def _compute_canceled_record_count(self):
        model_id = self.env['ir.model']._get_id(self._name)
        for record in self:
            cancellation_record_ids = record.env['cancellation.record'].sudo().search_fetch([('model_id','=', model_id),('record_id','=',record.id)], ['state'])
            record.record_cancellation_count = len(cancellation_record_ids)
            record.active_record_cancellation_count = len(cancellation_record_ids.filtered(lambda r: r.state not in ['approved', 'rejected']))         
                
    @api.depends('state','approval_state_id', 'last_state_update')
    def _calc_approval_activity_date_deadline(self):
        for record in self:
            if not record.approval_state_id.schedule_activity:
                record.approval_activity_date_deadline = False
            else:
                last_state_update = fields.Date.context_today(self, record.last_state_update)
                if record.approval_state_id.schedule_activity_field_id:
                    date_deadline = record[record.approval_state_id.schedule_activity_field_id.name] or last_state_update
                else:
                    date_deadline = last_state_update
                if record.approval_state_id.schedule_activity_days:
                    date_deadline += timedelta(days = record.approval_state_id.schedule_activity_days)
                record.approval_activity_date_deadline = date_deadline
                        
    def action_open_canceled_record(self):
        model_id = self.env['ir.model']._get_id(self._name)
        action = {
            'name': _('Cancellation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'cancellation.record',
            'domain':[('model_id','=', model_id),('record_id','=',self.id)]
        }
        if self.record_cancellation_count ==1:
            action.update({
                'res_id' : self.env['cancellation.record'].sudo().search(action['domain']).id,
                'views' : [(False, 'form')],
                'view_mode' : 'form'
            })
        return action
    
    @api.depends('last_state_update')
    def _calc_log_ids(self):
        model_id = self.env['ir.model']._get_id(self._name)        
        data = dict(self.env['approval.log']._read_group([('model_id','=', model_id), ('record_id','in', self.ids)], ['record_id'],['id:array_agg']))                
        for record in self:    
            ids = data.get(record.id)          
            record.log_ids = sorted(ids, reverse=True) if ids else False           
    
    @api.depends('write_uid')    
    def _calc_document_user_id(self):
        if 'employee_id' in self:
            for record in self:
                record.document_user_id = record.employee_id.user_id 
        elif 'create_uid' in self:
            for record in self:
                record.document_user_id = record.create_uid                                        
            
    @api.depends('state')
    def _calc_workflow_states(self):
        model_id = self.env['ir.model']._get_id(self._name) 
        state_ids = self.env['approval.config'].search_cached([('model_id','=', model_id), ('active','=', True)])
        for record in self:
            res = [record._get_draft_state()]
            if record.id:
                eval_context = record._get_eval_context()
                for approval_state_id in state_ids:
                    try:
                        eval_context['approval_state_id'] = approval_state_id
                        result = safe_eval(approval_state_id.condition, eval_context)
                    except Exception as ex:
                        _logger.error("Error evaluating workflow condition %s" % [self._name, approval_state_id.state] )
                        _logger.error(str(ex))
                        result = False
                    if result:
                        res.append(approval_state_id.state)
            res.append(record._get_approved_state())
            record.workflow_states = res
                    
    
    def _get_eval_context(self, approval_state_id = None):
        vals = self.env['ir.actions.actions']._get_eval_context()
        vals.update({
            'self' : self,
            'record' : self,
            'object' : self,
            'env' : self.env,
            'Warning': UserError,
            'UserError': UserError,
            'relativedelta' : relativedelta,
            'approval_state_id' : approval_state_id or self.approval_state_id
            })
        return vals
            
    
    @api.model
    def _before_approval_states_custom(self):
        if not self._get_approval_settings().static_states:
            return        
        model_id = self.env['ir.model']._get_id(self._name) 
        states=self.env['approval.settings.state'].sudo().search([('settings_id.model_id','=', model_id), ('type','=','before'), ('active','=', True)])
        if states:
            return [(state.state, state.name) for state in states]        
        return False
    
    @api.model
    def _before_approval_states(self):
        return self._before_approval_states_custom() or [('draft', _('Draft'))]
    
    @api.model
    def _after_approval_states_custom(self):
        if not self._get_approval_settings().static_states:
            return
        model_id = self.env['ir.model']._get_id(self._name) 
        states=self.env['approval.settings.state'].sudo().search([('settings_id.model_id','=', model_id), ('type','=','after'), ('active','=', True)])
        if states:
            return [(state.state, state.name) for state in states]                
        return False
    
    @api.model
    def _after_approval_states(self):       
        return self._after_approval_states_custom() or [('approved', _('Approved')), ('rejected', _('Rejected')), ('canceled', _('Canceled'))]    
    
    @api.model
    def _before_approval_states_values(self):
        return [state[0] for state in self._before_approval_states()]
    
    @api.model
    def _after_approval_states_values(self):
        return [state[0] for state in self._after_approval_states()]
                    
    @api.model
    def _approval_states(self):
        model_id = self.env['ir.model']._get_id(self._name)        
        records = self.env['approval.config'].sudo().search_cached([('model_id', '=', model_id), ('active','=', True)])
        return [(record.state, record.name) for record in records]

    @api.model
    def _non_approval_states(self):
        return self._before_approval_states_values() + self._after_approval_states_values()        
    
    @tools.ormcache()
    def _get_draft_state(self) -> str:
        values = self._before_approval_states_values()
        return values and values[0]    
    
    @tools.ormcache()
    def _get_reject_state(self) -> str:
        model_id = self.env['ir.model']._get_id(self._name) 
        reject_state_id = self.env['approval.settings.state'].search_cached([('model_id','=', model_id), ('type','=','after'), ('active','=', True), ('reject_state','=', True)])[:1]
        return reject_state_id.state or 'rejected'
    
    def _get_cancel_state(self) -> str:
        for state,__ in self._get_state():
            if 'cancel' in state:
                return state
        return ''
    
    @tools.ormcache()
    def _get_approved_state(self):
        return self._after_approval_states_values()[0]
            
    @api.depends('state')
    def _calc_approval_state_id(self):
        model_id = self.env['ir.model']._get_id(self._name)
        for record in self:
            record.approval_state_id = self.env['approval.config'].search_cached([('model_id','=', model_id), ('state','=', record.state)])                    
        
    @api.model  
    def _search_approval_state_id(self, operator, value):        
        if value is True:
            assert operator in ('=', '!=')
            value = False
            operator = operator=='=' and '!=' or '='            
        model_id = self.env['ir.model']._get_id(self._name)
        records = self.env['approval.config'].search([('id', operator, value), ('model_id', '=', model_id)])
        return [('state','in', records.mapped('state'))]
    
    @api.depends('state', 'approval_state_id')
    def _calc_waiting_approval(self):
        for record in self:
            record.waiting_approval = bool(record.approval_state_id)
            
    def _search_waiting_approval(self, operator, value):
        return [('approval_state_id', operator, value)]
    
    def _get_approval_groups(self):
        return self.approval_state_id.group_ids
            
    def _get_delegation_users(self, users: Users):
        return self.env['res.users']
                                     
    @api.depends('state', 'approval_state_id')
    def _calc_approval_user_ids(self):
        model_id = self.env['ir.model']._get_id(self._name)
        approval_forward_ids = self.env['approval.forward'].sudo().search_fetch([('model_id', '=', model_id), ('record_id', 'in', self.ids), ('active', '=', True)], ['user_id','record_id','approval_state_id'])
        
        for record in self:
            approval_state_id = record.approval_state_id.sudo()
            if approval_state_id:                                
                approval_forward_id = approval_forward_ids.filtered(lambda r: r.record_id == record.id and r.approval_state_id == approval_state_id)                
                if approval_forward_id:
                    user_ids = approval_forward_id.user_id                    
                else:
                    user_python_code = approval_state_id.user_python_code and approval_state_id.user_python_code.strip()      
                    user_ids = approval_state_id.user_ids           
                    
                    if user_python_code:
                        locals_dict = record._get_eval_context()
                        safe_eval(user_python_code, locals_dict, mode='exec', nocopy=True)
                        user_ids += locals_dict.get('result') or self.env['res.users']
                    else:
                        user_ids += approval_state_id.group_ids.users
                    
                    user_ids += record.sudo()._get_delegation_users(user_ids)
                                                                
                    for user in list(user_ids):
                        if not record.with_env(self.env(user = user, context={})).has_access('read'):
                            user_ids -=user
                
                approval_done_user_ids = self.env['res.users']
                if approval_state_id.committee:                   
                   for log in record.log_ids:
                       if log.new_state == log.old_state == record.state:
                           approval_done_user_ids |= log.user_id
                       else:
                           break                           
                   user_ids -= approval_done_user_ids
                                 
                record.approval_user_ids = user_ids
                record.user_can_approve = bool(user_ids & self.env.user) or self.env.user._is_superuser()                
                record.approval_partner_ids = user_ids.partner_id
                record.approval_done_user_ids = approval_done_user_ids
            else:
                record.approval_user_ids = False
                record.approval_partner_ids = False
                record.user_can_approve = False
                record.approval_done_user_ids = False
                
                    
    def _search_approval_user_ids(self, operator, value):
        user_ids = self.env['res.users'].search([('id', operator, value)])
        model_id = self.env['ir.model']._get_id(self._name)
        state_ids = self.env['approval.config'].search([('model_id','=', model_id), ('group_ids','in', user_ids.mapped('wkf_groups_ids.id'))])
        state_ids += self.env['approval.forward'].search([('model_id','=', model_id), ('user_id','in', user_ids.ids), ('active', '=', True)]).mapped('approval_state_id')
        ids = []
        for approval_state_id in state_ids:
            records= self.search([('state', '=', approval_state_id.state)])
            for record in records:
                if record.approval_user_ids & user_ids:
                    ids.append(record.id)                            
        return [('id', 'in', ids)]
    
    def _get_approval_settings(self):
        return self.env["approval.settings"].sudo().get(self._name)
    
    def _is_schedule_apprval_activity(self):
        return self.approval_state_id.schedule_activity
                        
    @on_state_updated()
    def _reschedule_approval_activity(self):                                
        self = self.with_context(mail_activity_quick_update = True).sudo()
        
        activity_type_approval = self.env.ref('oi_workflow.activity_type_approval')        
        model_id = self.env['ir.model']._get_id(self._name)
        
        for record in self:
            current_approval_activity_ids = record.activity_ids.filtered(lambda a: a.activity_type_id == activity_type_approval)
            if not record._is_schedule_apprval_activity():
                current_approval_activity_ids.unlink()
                continue
            for user in (record.approval_user_ids - current_approval_activity_ids.user_id):
                self.env['mail.activity'].create({
                    'res_id' : record.id,
                    'res_model_id' : model_id,
                    'activity_type_id' : activity_type_approval.id,
                    'summary' : self.env._('Waiting Approval'),
                    'automated' : True,
                    'date_deadline' : record.approval_activity_date_deadline,              
                    'user_id' : user.id,  
                })
            
            current_approval_activity_ids.filtered(lambda a: a.user_id not in record.approval_user_ids).unlink()
                            
    @api.model
    def _clean_actions(self, actions):                        
        actions = list(filter(lambda a : a and isinstance(a, dict), actions))
        if actions:
            if len(actions) > 1 and "ir.actions.act_multi" in self.env:
                return {
                    'type' : "ir.actions.act_multi",
                    'actions' : actions
                    }
            return actions[0]        
        
        if self.env.su and not self.env.user._is_superuser() and not self.with_user(self.env.user).has_access('read'):
            return {'type' : 'ir.actions.client', "tag" : "home"}            
                                        
        return {'type' : 'ir.actions.act_window_close'}
    
    def _change_state(self, new_state: str):
        self._old_state = self.state
        self.state = new_state
                        
    def _action_approve(self, force = False, clean_actions = True):    
        """
        approve record, change to next status

        Args:
            force (bool, optional): force to final/approve status . Defaults to False.
            clean_actions (bool, optional): return action instead of list of actions. Defaults to True.

        Returns:
            action or list of actions
        """
        actions = []    
        
        for record in self:
            
            if record.approval_state_id.committee and not force:        
                approval_done_user_ids = record.approval_done_user_ids | self.env.user
                remain_users = record.approval_user_ids - approval_done_user_ids

                if record.approval_state_id.committee_limit and record.approval_state_id.committee_limit >= len(approval_done_user_ids):
                    remain_users = False

                if record.approval_state_id.is_voting:
                    record._create_voting_record(record._approval_button_id.voting_type, record._approval_button_id.id)
                    
                actions.extend(record._apply_approval_trigger_methods('on_committee_approval'))
                voting_percentage = record.approval_voting_count / (len(record.approval_user_ids) + len(record.approval_done_user_ids)) * 100
                if remain_users:
                    record._create_approval_log(committee = True)
                    record.invalidate_recordset(['approval_user_ids','approval_done_user_ids', 'log_ids'])
                    record._reschedule_approval_activity()                                        
                    continue
                elif record.approval_state_id.is_voting and not remain_users and voting_percentage < record.approval_state_id.committee_vote_percentage:
                    record._action_reject()
                    continue
                else:
                    record._track_set_log_message('')
                                                                                                           
            next_state_id = record.approval_state_id._get_next(record) if not force else self.env["approval.config"]
            if next_state_id:
                new_state = next_state_id.state
            else:
                new_state = record._get_approved_state()                

            trigger_on_submit = not record.approval_state_id
                        
            record._change_state(new_state)

            if trigger_on_submit:
                actions.extend(record._apply_approval_trigger_methods('on_submit'))
            else:
                actions.extend(record._apply_approval_trigger_methods('on_approval'))
            
            if next_state_id:
                actions.extend(record._apply_approval_trigger_methods('on_enter_approval'))
            else:
                actions.extend(record._apply_approval_trigger_methods('on_approve'))
            
            if next_state_id.auto_approve and record.has_access('read') and record.user_can_approve:
                record._old_state = record.state
                actions.extend(record._action_approve(clean_actions = False))
                    
        return self._clean_actions(actions) if clean_actions else actions                                         
    
    def _action_change_state(self, new_state: str, trigger: str):
        actions = []
        for record in self:
            record.state = new_state
            actions.extend(record._apply_approval_trigger_methods(trigger))
        return self._clean_actions(actions)
    
    def _action_reject(self):    
        return self._action_change_state(self._get_reject_state(), 'on_reject')
    
    def _action_return(self, return_state: str = None):        
        return self._action_change_state(return_state or self._approval_button_id.return_state, 'on_return')
                                           
    def _action_cancel(self):    
        return self._action_change_state(self._get_cancel_state(), 'on_cancel')
    
    def _action_draft(self):    
        return self._action_change_state(self._get_draft_state(), 'on_draft')       
    
    def _action_transfer(self, transfer_state: str):        
        return self._action_change_state(transfer_state, 'on_transfer')     
    
    def _action_cancel_workflow(self, reason = None):
        if self.active_record_cancellation_count:
            raise UserError(_('Record cancellation workflow already started'))
        
        cancellation_record = self.env["cancellation.record"].create({
            'record_id' : self.id,
            'model_id' : self.env["ir.model"]._get(self._name).id,
            'reason' : reason
        })
        cancellation_record._action_approve()
        return {"type" : "ir.actions.client","tag" : "soft_reload"}                    
    
    def _action_email(self, next_action = False):
        if next_action:
            return getattr(self,f"_action_{self._approval_button_id.email_next_action}")()
        
        template = self._approval_button_id.email_template_id
        compose_form = self._approval_button_id.email_wizard_form_id or self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model= self._name,
            default_res_ids=self.ids,
            default_template_id=template.id if template else False,
            default_composition_mode='comment',
            approval_button_id = self._approval_button_id.id
        )
        return {
            'name': self._approval_button_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
    
    def _prepare_approval_forward_vals(self, forward_user_id):
        return {
                'record_id' : self.id,
                'model_id' : self.env["ir.model"]._get(self._name).id,
                'forwarder_user_id' : self.env.user.id,
                'approval_state_id' : self.approval_state_id.id,
                'user_id' : forward_user_id.id
            }
        
    def _action_forward(self, forward_user_id):    
        if isinstance(forward_user_id, int):
            forward_user_id = self.env['res.users'].browse(forward_user_id)                
        
        actions = []
        for record in self:
            self.env['approval.forward'].create(record._prepare_approval_forward_vals())
            
            if not record.with_user(forward_user_id).has_access('read'):
                raise UserError(self.env._('User %s not have access to record %s', forward_user_id.display_name, record.display_name))
            
            record._post_approval_forward(forward_user_id)
            actions.extend(record._apply_approval_trigger_methods('on_forward'))
        return self._clean_actions(actions)
    
    def _action_action(self):      
        return self._approval_button_id.server_action_id.with_context(active_model = self._name, active_ids = self.ids, active_id = self[:1].id).run()                                                                                                    
        
    @api.ondelete(at_uninstall=False)
    def _unlink_check_status(self):
        for record in self:
            if record.state != self._get_draft_state() and record.state != "cancel":
                raise ValidationError(_('You can delete in %s status only') % self._get_draft_state())                
    
    @api.ondelete(at_uninstall=False)
    def _unlink_remove_approval_log(self):
        model_id = self.env['ir.model']._get_id(self._name)
        self.env['approval.log'].sudo().search([('model_id','=', model_id), ('record_id', 'in', self.ids)]).unlink()            
                                                     
    def action_approve_all(self):            
        self = self.with_context(approval_all_action = True)
        approval_buttons = self.env["approval.buttons"].sudo().search([('model','=', self._name), ('active','=', True), ('action_type','=', 'approve')])
        for record in self:
            if record.user_can_approve or record.state == record._get_draft_state():
                for button in approval_buttons:
                    button._ensured_cached()
                    if not button._is_invisible(record) and not button.show_process_wizard:                                          
                        record.approval_action_button(button.id)
                        break
        return {
            "type" : "ir.actions.client",
            "tag" : "soft_reload"
        }
                    
    @api.model    
    def _add_approval_fields(self, header): 
        for fname in ["workflow_states", "user_can_approve", "document_user_id", 'record_cancellation_count', "approved_button_clicked", "approval_visible_button_ids"]:
            field = etree.Element("field", name=fname, invisible="1", readonly="1")
            field.tail = '\n'
            header.append(field)                
            
    @api.model    
    def _add_approval_user_info_button(self, header):
        button_attr = {
            'name' : "",
            'string' : "",
            'invisible' : f"not waiting_approval",
            'type' : 'action',
            'class' : "btn-link btn-info",
            'icon' : "fa-users",
            'id' : 'approval_user_info'
        }
        ebutton = etree.Element("button", **button_attr)
        ebutton.tail = '\n'
        header.append(ebutton)                
            
    @api.model    
    def _add_approval_buttons(self, header):
        for button in self.env["approval.buttons"].sudo().search_cached([('model','=', self._name), ('active','=', True)]):
            if not button._user_button_access():
                continue
            button_attr = {
                'name' : f"approval_action_button",
                'string' : button.name,
                'invisible' : button.invisible or '0',
                'type' : 'object',
                'class' : button.button_class or '',
                'confirm' : button.confirm_message if button.confirm_message and not button.comment else '',
                'context' : button.context or '',
                'args' : json.dumps([button.id]),
                'icon' : button.icon or '',
                'id' : f"approval_button_{button.id}",
                "validate_form" : str(button.validate_form)
            }
            if button.hotkey:
                button_attr['data-hotkey'] = button.hotkey
            ebutton = etree.Element("button", **button_attr)
            ebutton.tail = '\n'
            header.append(ebutton)                                                         
        
    @api.model    
    def _add_record_cancellation_button(self, button_box):
        button = etree.Element("button", name='action_open_canceled_record', type="object", 
                                invisible="record_cancellation_count == 0", 
                                icon="fa-remove", **{'class' : 'oe_stat_button'})
        
        
        record_cancellation_count = etree.Element("field", name="record_cancellation_count", readonly="1", widget="statinfo", string=self.env._("Cancellation"))
        button.append(record_cancellation_count)
        
        button_box.append(button)         
        
    @api.model    
    def _add_apprval_servey_button(self, button_box):               
        pass
    
    @api.model    
    def _approval_add_button_box(self, sheet):
        if button_box := sheet.xpath(".//div[@name='button_box']"):
            button_box = button_box[0]
        else:
            button_box = etree.Element("div", name='button_box', **{'class' : 'oe_button_box'})
            sheet.insert(0, button_box)
        
        self._add_record_cancellation_button(button_box)
        self._add_apprval_servey_button(button_box)        
        
        return button_box
    
    def _set_form_field_readonly(self, arch):
        """Sets readonly attribute on form fields based on certain conditions.
        This method modifies the XML architecture of a form view by setting readonly attributes
        on field nodes. It processes all field nodes in the form recursively and sets them as
        readonly if they meet specific criteria.
        Args:
            arch (lxml.etree.Element): The XML architecture node representing the form view
        Returns:
            None
        Notes:
            - Only processes fields if self._default_field_readonly is set
            - Skips fields that are:
                * Already marked as readonly
                * Marked as invisible (value '0' or 'False')
                * Named 'state'
            - Only sets readonly on fields that are not already readonly in their field definition
        """
        if not self._default_field_readonly:
            return
        
        def get_form_fields(node):            
            for child in node.getchildren():
                if child.tag == "field":
                    yield child
                else:
                    yield from get_form_fields(child)                        
        
        for field_node in get_form_fields(arch):
            if field_node.get('invisible') in ['0','False'] or field_node.get('readonly') or field_node.get('name') in ['state']:
                continue
            field = self._fields.get(field_node.get('name'))
            if field and not field.readonly:
                field_node.set("readonly", self._default_field_readonly)                                           
            
                
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
                
        if not options.get('studio'):
            
            approval_settings_id = self._get_approval_settings()
            
            if view_type == 'form':
                self._set_form_field_readonly(arch)
                
                if sheet := arch.xpath("//sheet"):
                    sheet = sheet[0]
                    self._approval_add_button_box(sheet)
                                                                                                                
                if header := arch.xpath("//header"):       
                    header = header[0]         
                    self._add_approval_buttons(header)
                    self._add_approval_user_info_button(header)   
                    self._add_approval_fields(header)         
                    
                    if state_field := header.xpath(".//field[@name='state']"):
                        state_field = state_field[0]
                        if approval_settings_id.show_status_duration_tracking:
                            state_field.set("widget", "statusbar_state_duration")                                                        
                        if approval_settings_id.dynamic_statusbar_visible:
                            state_field.set("statusbar_visible", "WORKFLOW")                             
                                    
            
            elif view_type == 'list':
                if approval_settings_id.is_show_action_approve_all():
                    list_node = arch.xpath("//list")
                    if list_node:
                        list_node[0].set("show_action_approve_all", "true")
        
        elif view_type == "form":
            if header := arch.xpath("//header"):       
                self._add_approval_fields(header)                                 
        
        return arch, view         

    @property
    def _approval_trigger_methods(self):
        triggers = self.env.registry["approval.automation"]._fields['trigger'].get_values(self.env)
        
        cls = self.env.registry[self._name]
        methods = defaultdict(list)
        for attr, func in getmembers(cls, callable):
            for name in triggers:
                if hasattr(func, f'_approval_{name}'):
                    methods[name].append(func)
        
        cls._approval_trigger_methods = methods # pyright: ignore[reportAttributeAccessIssue]
        return methods
                                
    def _apply_approval_trigger_methods(self, trigger: str) -> list :
        assert trigger in self.env["approval.automation"]._fields['trigger'].get_values(self.env)
        actions = []                   
        
        old_state = self._old_state or self.state
        new_state = self.state
        
        def get_states(states):
            if callable(states):
                states = states(self)
            if isinstance(states, str):
                states = states.split(",")
            if states is False:
                return (".",)
            return states
        
        for method in self._approval_trigger_methods.get(trigger, ()):
            old_states, new_states = getattr(method, f'_approval_{trigger}')
            old_states = get_states(old_states)
            new_states = get_states(new_states)                                    
            if old_states and old_state not in old_states:
                continue
            if new_states and new_state not in new_states:
                continue
            if config['dev_mode']:
                _logger.info(f"_apply_approval_trigger_methods {trigger} {self} {method}")
            res = method(self)
            if res:
                actions.append(res)
        
        return actions
    
    def approval_action_button(self, button_id: int, ignore_comment=None, **kwargs):
        self.ensure_one()
        self.check_access('read')
        button = self.env['approval.buttons'].browse(button_id).sudo()
        button._ensured_cached()
            
        if button._is_invisible(self):
            return {"type" : "ir.actions.client","tag" : "soft_reload"}                    
        
        if not ignore_comment and button.show_process_wizard:
            return {
                'type' : 'ir.actions.act_window',
                'name' : button.display_name,
                'res_model' : 'approval.process.wizard',
                'target' : 'new',
                'view_mode' : 'form',
                'context' : {
                    'default_button_id' : button.id,
                    'default_res_model' : self._name,
                    'default_res_ids' : self.ids,
                    'default_confirm_message' : button.confirm_message,
                }
            }
        
        if button.run_as_superuser:            
            self = self.sudo()
            
        self._approval_button_id = button
        if button.action_type == "method":
            return getattr(self,f"{button.method}")()
        return getattr(self,f"_action_{button.action_type}")(**kwargs)
        
    
    def modified(self, fnames, create=False, before=False):        
        if 'state' in fnames and all(self._ids):
            if create:
                for record in self:
                    record._apply_approval_trigger_methods('on_create')            
                
            else:
                if before:
                    for record in self:
                        if not record._old_state:
                            record._old_state = record.state            
                else:
                    for record in self:
                        record._apply_approval_trigger_methods('on_state_updated')
                                
        return super().modified(fnames, create, before)
    
    def _prepare_approval_log_vals(self):
        model_id = self.env['ir.model']._get_id(self._name)
        approval_all_action = bool(self._context.get('approval_all_action'))
        now = self.env.cr.now()
        duration_seconds = (now - self.last_state_update).total_seconds()
        return {
            'record_id' : self.id,
            'user_id' : self.env.user.id,
            'date' : now,
            'new_state' : self.state,
            'old_state' : self._old_state or self.state,
            'model_id' : model_id,
            'description' : self._approval_comment,
            'duration_seconds' : duration_seconds,
            'duration_hours': duration_seconds / 3600,
            'approval_button_id' : self._approval_button_id.id,
            'bulk_approval' : approval_all_action                
        }
        
    @on_state_updated()
    def _create_approval_log(self, committee = False):
        for record in self:            
            self.env['approval.log'].sudo().create(record._prepare_approval_log_vals())        
            if not committee:            
                record.last_state_update = self.env.cr.now()
                
    @on_state_updated()
    def _remove_approval_forward(self):
        model_id = self.env['ir.model']._get_id(self._name)
        self.env['approval.forward'].sudo().search([('model_id','=', model_id),('record_id','in', self.ids),('active','=', True)]).write({'active' : False})     
           
    @on_committee_approval()     
    def _post_committee_approval(self):
        for record in self:
            icon = record._approval_button_id.icon or 'fa-thumbs-up'
            class_name = record._approval_button_id.button_class.replace('btn', 'text')
            comment = record._approval_comment
            message = record._approval_button_id.name or self.env._("Approved")
            record.message_post(body=Markup(f'<span>{message} <i class="fa {icon} {class_name}"></i> </span> <br> {comment}'))
            
    def _post_approval_forward(self, forward_user_id):
        for record in self:
            record.message_post(body=self.env._("Approval forwarded to %s", forward_user_id.display_name))            
                
    @api.depends('log_ids')
    def _calc_duration_state_tracking(self):        
        for record in self:
            duration = defaultdict(float)
            last_state_update = record.create_date
            
            for log in record.log_ids.sorted('id'):
                duration[log.old_state] += (log.date - last_state_update).total_seconds()
                last_state_update = log.date
            
            duration[record.state] += (self.env.cr.now() - last_state_update).total_seconds()
            record.duration_state_tracking = duration

    def _create_voting_record(self, vote_type, button_id):
        self.env['approval.log.voting'].create({
            'user_id': self.env.user.id,
            'vote': vote_type,
            'button_id': button_id,
            'model_id': self.env['ir.model']._get_id(self._name),
            'record_id': self.id,
            'comment': self._approval_comment,
            'state': self.state,
        })
        
    def approval_action_submit(self):
        if self.state == self._get_draft_state():
            return self._action_approve()
        
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get("approval_auto_submit"):
            records._action_approve()
        return records
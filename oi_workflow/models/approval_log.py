
from collections import defaultdict
from odoo import models, fields, api
from odoo.tools import create_index
from odoo.osv.expression import FALSE_DOMAIN, OR
import humanize
from datetime import timedelta
import re

class ApprovalLog(models.Model):
    _name = 'approval.log'
    _description = 'Approval Log'
    _log_access = False
    _order = 'id desc'
    
    model_id = fields.Many2one('ir.model', string='Object', required = True, ondelete='cascade')
    model = fields.Char(related = 'model_id.model', compute_sudo = True)
    record_id = fields.Many2oneReference(required = True, model_field="model")
    user_id = fields.Many2one('res.users', 'User', required = True)
    date = fields.Datetime('Date', required = True)
    description = fields.Char()
    
    old_state = fields.Char('Old Status (Value)')
    new_state = fields.Char('New Status (Value)')
    
    old_status = fields.Char('Old Status', compute = '_compute_status_name', search = '_search_old_status')
    new_status = fields.Char('New Status', compute = '_compute_status_name', search = '_search_new_status')
    
    duration_seconds = fields.Float('Duration (Seconds)')
    duration_hours = fields.Float('Duration (Hours)')
    duration = fields.Char(compute ="_calc_duration")
    
    duration_hours_avg = fields.Float(related="duration_hours", string="Average Duration (Hours)", aggregator='avg')
    duration_seconds_avg = fields.Float(related="duration_hours", string="Average Duration (Seconds)", aggregator='avg')
    
    approval_button_id = fields.Many2one("approval.buttons", string="Button")
    
    bulk_approval = fields.Boolean()
            
    def _auto_init(self):
        res = super()._auto_init()
        create_index(self._cr, 'approval_log_res_idx', self._table, ['model_id', 'record_id'])
        return res
    
    @api.depends('duration_seconds')
    def _calc_duration(self):
        if self.env.lang and self.env.lang != 'en_US':
            try:
                humanize.i18n.activate(self.env.lang)
            except:
                humanize.i18n.deactivate()
        else:
            humanize.i18n.deactivate()
            
        for record in self:
            delta = timedelta(seconds=record.duration_seconds)
            if delta.days > 30:
                minimum_unit = "days"
            elif delta.days:
                minimum_unit = "hours"
            elif record.duration_seconds / 3600 >= 1:
                minimum_unit = "minutes"                
            else:
                minimum_unit = "seconds"
            record.duration = humanize.precisedelta(delta, minimum_unit = minimum_unit)
             
    @api.depends('model', 'new_state', 'old_state')
    def _compute_status_name(self):
        for model, records in self.grouped('model').items():
            try:
                vals = dict(self.env[model]._fields['state']._description_selection(self.env))
            except KeyError:
                vals = {}
            for record in records:
                record.new_status = vals.get(record.new_state, record.new_state)                           
                record.old_status = vals.get(record.old_state, record.old_state)                                  
                
    def _status_compare(self, name, comparator, value):
        if comparator in ('like', 'ilike', '=like', '=ilike', 'not ilike', 'not like'):
            if comparator.endswith('ilike'):
                # ilike uses unaccent and lower-case comparison
                # we may get something which is not a string
                def unaccent(x):
                    return self.pool.unaccent_python(str(x).lower()) if x else ''
            else:
                def unaccent(x):
                    return str(x) if x else ''
                
            def build_like_regex(value: str, exact: bool):
                yield '^' if exact else '.*'
                escaped = False
                for char in value:
                    if escaped:
                        escaped = False
                        yield re.escape(char)
                    elif char == '\\':
                        escaped = True
                    elif char == '%':
                        yield '.*'
                    elif char == '_':
                        yield '.'
                    else:
                        yield re.escape(char)
                if exact:
                    yield '$'
                # no need to match r'.*' in else because we only use .match()

            like_regex = re.compile("".join(build_like_regex(unaccent(value), comparator.startswith("="))))
            
            ok = like_regex.match(unaccent(name))
            if comparator.startswith('not'):
                ok = not ok
            return ok
                
        if comparator == '=':
            if value is False:
                return False
            return name == value
        
        if comparator != '=':
            if value is False:
                return True            
            return name != value                
                                        
    def _get_search_status_domain(self, field: str, operator: str, value: str):
        value = value or ""
        states = defaultdict(list)
        model_ids = self.env['ir.model'].search_fetch([('is_approval_record','=', True)], ['model'])
        for model_id in model_ids:
            for state,name in self.env[model_id.model]._get_state():
                if self._status_compare(name, operator, value):
                    states[model_id].append(state)
        if not states:
            return FALSE_DOMAIN
        
        domains = [[('model_id','=', model_id.id), (field,'in', states)] for (model_id, states) in states.items()]
        return OR(domains)
                    
    def _search_new_status(self, operator, value):
        return self._get_search_status_domain('new_state', operator, value)
                
    def _search_old_status(self, operator, value):
        return self._get_search_status_domain('old_state', operator, value)
                
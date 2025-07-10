
from odoo import models, api, tools
from odoo.tools.misc import frozendict

class CacheMixin(models.AbstractModel):
    _name = 'cache.mixin'
    _description = 'Cache Mixin'
    
    @api.model
    @tools.ormcache('tuple(domain)')
    def _search_cached(self, domain):
        return self.sudo().with_context(active_test = False).search(domain)._ids
    
    @api.model
    @tools.ormcache('record_id', 'self.env.lang')
    def _read_cached(self, record_id):
        vals = self.sudo().browse(record_id).read([])[0]
        for name, value in vals.items():
            vals[name] = self._fields[name].convert_to_cache(value, self)
        return frozendict(vals)
    
    def _ensured_cached(self):
        vals = self._read_cached(self.id)
        for name,value in vals.items():
            field = self._fields[name]
            self.env.cache.insert_missing(self, field, [value])
            
    @api.model                                          
    def search_cached(self, domain):
        ids = self._search_cached(domain)
        for record_id in ids:
            record = self.browse(record_id)
            record._ensured_cached()        
        return self.browse(ids)                            
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super(CacheMixin, self).create(vals_list)
        self.env.registry.clear_cache() 
        if getattr(self, '_auto_update_registry', False):
            self._update_registry()        
        return res

    def write(self, vals):
        res = super(CacheMixin, self).write(vals)
        self.env.registry.clear_cache()
        if getattr(self, '_auto_update_registry', False):
            self._update_registry()
        return res
    
    @api.ondelete(at_uninstall=False)
    def _unlink_clear_cache(self):
        self.env.registry.clear_cache()
        if getattr(self, '_auto_update_registry', False):
            self._update_registry()        
                
    def _update_registry(self):
        if self.env.registry.ready:
            self.env.flush_all()
            self.env.registry.clear_cache() 
            self.env.registry.registry_invalidated = True
            self.env.registry.setup_models(self.env.cr)            
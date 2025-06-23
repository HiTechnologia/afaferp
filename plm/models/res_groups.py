
from odoo.osv.expression import AND
from odoo import models
from odoo import fields
from odoo import api
from odoo import _


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    @api.returns('self')
    def search(self, args, offset=0, limit=None, order=None):
        if self.env.context.get('odooPLM'):
            available_types = [
                self.env.ref('plm.group_plm_view_user').id,
                self.env.ref('plm.group_plm_integration_user').id,
                self.env.ref('plm.group_plm_admin').id,
                self.env.ref('plm.group_plm_readonly_released').id,
                self.env.ref('plm.group_plm_release_users').id,
                ]
            additional_xml_refs = [
                'plm_automatic_weight.group_plm_weight_admin',
                'activity_validation.group_force_activity_validation_admin',
                'activity_validation.group_force_activity_validation_user',
                'activity_validation.group_force_activity_validation_user_readonly',
                ]
            for additional_xml_ref in additional_xml_refs:
                additional_obj = self.env.ref(additional_xml_ref, False)
                if additional_obj:
                    available_types.append(additional_obj.id)
            args = AND([args, [('id', 'in', available_types)]])
        return super(ResGroups, self).search(args, offset, limit, order)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
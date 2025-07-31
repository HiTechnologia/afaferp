from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def export_to_excel(self):
        all_leads = self.env['crm.lead'].search([])
        lead_ids = ','.join(map(str, all_leads.ids))
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/crm.lead/export_excel?ids={lead_ids}",
            'target': 'new',
        }
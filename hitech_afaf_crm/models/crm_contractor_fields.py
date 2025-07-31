from odoo import models, fields, api


class CrmContractorLine(models.Model):
    _name = 'crm.contractor.line'
    _description = 'Contractor Info Line'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    contractor_id = fields.Many2one('res.partner', domain="[('is_company','=',True)]", required=True)
    date_received = fields.Date()
    week_ref_label = fields.Char(compute="_compute_week_label", store=True)

    @api.depends('date_received')
    def _compute_week_label(self):
        for rec in self:
            if rec.date_received:
                dt = rec.date_received
                day = dt.day
                week_of_month = ((day - 1) // 7) + 1  # 1-based index

                # Optional: uppercase suffix
                suffix = f"{week_of_month}TH"
                rec.week_ref_label = f"{suffix}/{dt.year}"
            else:
                rec.week_ref_label = ''

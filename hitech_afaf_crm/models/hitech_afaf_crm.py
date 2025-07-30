from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    project_id = fields.Many2one('project.project', string='Project')
    project_code = fields.Char(related='project_id.ht_project_code', string="Project Code", store=True)
    project_plot = fields.Char(related='project_id.ht_project_plot', string="Plot No.")
    project_detail = fields.Char(related='project_id.ht_project_detail', string="Project Details")

    # Manually set this
    week_ref = fields.Date(string='Week REF Date', help="Any date within the week to auto-generate a week label.")
    # Auto-generated label like 2ND/1/2025
    week_ref_label = fields.Char(string='Week REF#', compute='_compute_week_ref_label', store=True)
    selected_by_mngt = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('pending', 'Pending')
    ], string='Selected By MGMT')
    date_received = fields.Date(string='Date Received')
    contractor = fields.Many2many(
        'res.partner',
        'crm_lead_contractor_rel',
        'lead_id', 'partner_id',
        string="Contractors"
    )
    consultant = fields.Many2one(
        'res.partner',
        string="Consultant"
    )

    ht_type = fields.Selection([
        ('tender', 'Tender'),
        ('job_in_hand', 'Job in Hand'),
    ], string='Type')

    quoted = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('ongoing', 'Ongoing'),
        ('tba', 'TBA')
    ], string='Quoted')

    is_approved = fields.Boolean(string="Admin Approved", default=False)

    @api.depends('week_ref')
    def _compute_week_ref_label(self):
        for rec in self:
            if rec.week_ref:
                day = rec.week_ref.day
                month = rec.week_ref.month
                year = rec.week_ref.year

                if 1 <= day <= 7:
                    suffix = "1ST"
                elif 8 <= day <= 14:
                    suffix = "2ND"
                elif 15 <= day <= 21:
                    suffix = "3RD"
                elif 22 <= day <= 28:
                    suffix = "4TH"
                else:
                    suffix = "5TH"

                rec.week_ref_label = f"{suffix}/{month}/{year}"
            else:
                rec.week_ref_label = False

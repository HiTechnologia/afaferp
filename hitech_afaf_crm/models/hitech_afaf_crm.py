from odoo import models, fields, api
from datetime import datetime

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    project_id = fields.Many2one('project.project', string='Project')
    project_code = fields.Char(related='project_id.ht_project_code', string="Project Code", store=True)
    project_plot = fields.Char(related='project_id.ht_project_plot', string="Plot No.")
    project_detail = fields.Char(related='project_id.ht_project_detail', string="Project Details")
    contractor_line_ids = fields.One2many('crm.contractor.line', 'lead_id', string="Contractors")

    # Manually set this
    # Auto-generated label like 2ND/1/2025
    selected_by_mngt = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('pending', 'Pending')
    ], string='Selected By MGMT')
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
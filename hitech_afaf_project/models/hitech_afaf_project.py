from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    ht_project_code = fields.Char(string="Project Code")
    ht_project_plot = fields.Char(string="Plot No.(Project)")
    ht_project_detail = fields.Char(string="Project Details")
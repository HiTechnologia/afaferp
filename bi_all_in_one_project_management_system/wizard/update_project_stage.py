# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class MassUpdateProjectStages(models.TransientModel):
    _name = 'mass.update.project.stage'
    _description = 'Mass Update Project Stages'

    is_update = fields.Boolean(string="Mass Update Project",default=False)
    project_ids = fields.Many2many('project.project',string='Project')
    project_update_method = fields.Selection(
        [('add', 'Add'), ('replace', 'Replace')], 'Project Update Method', default='add',
        required=True)

    def update_project_stage(self):
        active_ids = self._context.get('active_ids', [])
        project_ids = self.env['project.task.type'].browse(active_ids)
        for project in project_ids:
            if self.is_update == True:
                if self.project_update_method == 'add':
                    project.project_ids = [(4, update_project) for update_project in self.project_ids.ids]
                if self.project_update_method == 'replace':
                    project.project_ids = [(6, 0, self.project_ids.ids) or []]
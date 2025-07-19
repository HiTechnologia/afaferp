# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, tools, _


class MassUpdateTaskWizard(models.TransientModel):

	_name='mass.update.task.wiz'
	_description = "Mass Update Task"

	change_project = fields.Boolean('Change Project')
	project_id = fields.Many2one(comodel_name='project.project', string='Select Project')
	
	change_deadline = fields.Boolean('Change Deadline')
	new_date_deadline = fields.Date(string='New Date Deadline')
	
	change_stage = fields.Boolean('Change Stage')
	new_stage = fields.Many2one('project.task.type', 'Select New Stage')
	
	
	change_assignees = fields.Boolean('Change Assignees')
	update_assignees_via = fields.Selection([('add', 'Add'), ('replace', 'Replace')], 'Update Via')
	assignees_ids = fields.Many2many('res.users', 'wiz_assignees_rel')
	
	change_tag = fields.Boolean('Change Tag')
	update_tag_via = fields.Selection([('add', 'Add'), ('replace', 'Replace')], 'Update Via ')
	tags = fields.Many2many('project.tags', 'wiz_tags_rel')
	
	
	
	
	

	


	def update_values(self):
		if self._context.get('active_model') == 'project.task':
			all_task_ids = self.env['project.task'].browse(self._context.get('active_ids'))
			
			for obj in all_task_ids:
				if self.change_project:
					obj.project_id = self.project_id.id
					
				if self.change_deadline:
					obj.date_deadline = self.new_date_deadline
				
				if self.change_stage:
					obj.stage_id = self.new_stage.id
		
				if self.change_tag:
					if self.update_tag_via == 'add':
						obj.tag_ids = [(4, i) for i in self.tags.ids]
					if self.update_tag_via == 'replace':
						obj.tag_ids = [(6, 0, self.tags.ids) or []]
						
				if self.change_assignees:
					if self.update_assignees_via == 'add':
						obj.user_ids = [(4, i) for i in self.assignees_ids.ids]
					if self.update_assignees_via == 'replace':
						obj.user_ids = [(6, 0, self.assignees_ids.ids) or []]
		return True
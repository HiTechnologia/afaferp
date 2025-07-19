# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from odoo import api, fields, models, _
from datetime import datetime, timedelta ,date
import calendar

class ResUsers(models.Model):
	_inherit = "res.users"

	assign_update_ids = fields.One2many('task.update','assign_task_id')
	created_task_ids = fields.One2many('task.update','create_task_id')

	def task_update_email(self):
		superuser_id = self.env['res.partner'].browse(SUPERUSER_ID)
		
		user_ids = self.env['res.users'].search([('active','=',True),('share','=',False)])

		for user in user_ids:
			create_task_ids = self.env['task.update']
			task_list_ids = self.env['task.update']

			task_ids = self.env['project.task'].search(['|',('user_ids','=',user.id),('create_uid','=',user.id)])
			
			if task_ids:
				for task in task_ids.filtered(lambda x : x.user_ids == user):
					today = datetime.now().date()
					overdue_days = ''
					if task.date_deadline:
						days=today -task.date_deadline.date()
						overdue_days=days.days
						task_list_ids += self.env['task.update'].create({'name':task.name,
							'date_deadline':task.date_deadline,
							'stage_id':task.stage_id.id,
							'dueday':overdue_days,
							'assign_task_id' : user.id
						})

				for task in task_ids.filtered(lambda x : x.create_uid == user):
					today = datetime.now().date()
					overdue_days = ''
					if task.date_deadline:
						days=today -task.date_deadline.date()
						overdue_days=days.days
						create_task_ids += self.env['task.update'].create({'name':task.name,
							'date_deadline':task.date_deadline,
							'stage_id':task.stage_id.id,
							'dueday':overdue_days,
							'create_task_id' : user.id
						})

				user.sudo().write({
					'created_task_ids' : [(6,0,create_task_ids.ids)],
					'assign_update_ids' : [(6,0,task_list_ids.ids)]
				})

				template_id = self.env['ir.model.data']._xmlid_lookup(
														'bi_all_in_one_project_management_system.email_template_task_update')[1]
				email_template_obj = self.env['mail.template'].browse(template_id)
				if template_id:
					values = email_template_obj._generate_template([user.id],('subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'))[user.id]
					values['email_to'] = user.partner_id.email
					values['res_id'] = False
					values['author_id'] = user.partner_id.id
					mail_mail_obj = self.env['mail.mail']
					mail_create_id = mail_mail_obj.sudo().create(values)
					if mail_create_id:
						mail_create_id.sudo().send()
		return True



	def weekly_task_update_email(self):
	    superuser_id = self.env['res.partner'].browse(SUPERUSER_ID)

	    user_ids = self.env['res.users'].search([('active', '=', True), ('share', '=', False)])

	    for user in user_ids:
	        create_task_ids = self.env['task.update']
	        task_list_ids = self.env['task.update']

	        task_ids = self.env['project.task'].search(['|', ('user_ids', '=', user.id), ('create_uid', '=', user.id)])

	        if task_ids:
	            today = datetime.now().date()  # Get today's date

	            for task in task_ids.filtered(lambda x: x.user_ids == user):
	                overdue_days = ''
	                if task.date_deadline:
	                    days = today - task.date_deadline.date()  # Ensure date comparison
	                    overdue_days = days.days
	                    task_list_ids += self.env['task.update'].create({
	                        'name': task.name,
	                        'date_deadline': task.date_deadline,
	                        'stage_id': task.stage_id.id,
	                        'dueday': overdue_days,
	                        'assign_task_id': user.id
	                    })

	            for task in task_ids.filtered(lambda x: x.create_uid == user):
	                overdue_days = ''
	                if task.date_deadline:
	                    days = today - task.date_deadline.date()  # Ensure date comparison
	                    overdue_days = days.days
	                    create_task_ids += self.env['task.update'].create({
	                        'name': task.name,
	                        'date_deadline': task.date_deadline,
	                        'stage_id': task.stage_id.id,
	                        'dueday': overdue_days,
	                        'create_task_id': user.id
	                    })

	            user.sudo().write({
	                'created_task_ids': [(6, 0, create_task_ids.ids)],
	                'assign_update_ids': [(6, 0, task_list_ids.ids)]
	            })

	            template_id = self.env['ir.model.data']._xmlid_lookup(
	                'bi_all_in_one_project_management_system.email_template_task_update')[1]
	            email_template_obj = self.env['mail.template'].browse(template_id)
	            if template_id:
	                values = email_template_obj._generate_template(
	                    [user.id], ('subject', 'body_html', 'email_from', 'email_to', 
	                                'partner_to', 'email_cc', 'reply_to', 'scheduled_date')
	                )[user.id]
	                values['email_to'] = user.partner_id.email
	                values['res_id'] = False
	                values['author_id'] = user.partner_id.id
	                mail_mail_obj = self.env['mail.mail']
	                mail_create_id = mail_mail_obj.sudo().create(values)
	                if mail_create_id:
	                    mail_create_id.sudo().send()
	    return True


	
		
		
class Task_updates(models.Model):
	_name='task.update'
	_description="Task Updates"

	name=fields.Char(string='name')
	date_deadline=fields.Date(string='Date Deadline')
	stage_id = fields.Many2one('project.task.type', string='Stage')
	dueday=fields.Char(string='Overdue')
	assign_task_id=fields.Many2one('res.users')
	create_task_id=fields.Many2one('res.users')

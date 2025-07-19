from odoo import fields , models , api , _
from ast import literal_eval
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta

from odoo import models, fields


class ResCompany(models.Model):
	_inherit = 'res.company'

	start_notification = fields.Boolean(string='Delay Task Start Notification', default=False)
	delay_notification = fields.Boolean(string='Delay Task Deadline/Overdue Notification', default=False)
	start_count = fields.Integer(string='Delay Day(s)', default=0)
	delay_count = fields.Integer(string='Delay Deadline Day(s)', default=0)
	done_stage_ckecklist = fields.Many2one('project.task.type', 'Done Stage')
	todo_stage_ckecklist = fields.Many2one('project.task.type', 'To Do Stage')
	cancel_stage_ckecklist = fields.Many2one('project.task.type', 'Cancel Stage')
	warning_child_task = fields.Many2one('project.task.type',
										 'Prevent stage to change until all tasks on the same stage')

	first_reminder = fields.Float(string='First Reminder (Days)')
	second_reminder = fields.Float(string='Second Reminder (Days)')
	first_date = fields.Date(compute='convert_first_date')
	second_date = fields.Date(compute='convert_second_date')
	allow_multi_task = fields.Boolean(string='Allow Multi Task')



class ResConfigSettings(models.TransientModel):
	_inherit = "res.config.settings"
	_description="Res config Settings"

	start_notification = fields.Boolean(string='Delay Task Start Notification', related='company_id.start_notification', default=False)
	delay_notification = fields.Boolean(string='Delay Task Deadline/Overdue Notification', related='company_id.delay_notification',	default=False)
	start_count = fields.Integer(string='Delay Day(s)',	related='company_id.start_count', default=0)
	delay_count = fields.Integer(string='Delay Deadline Day(s)', related='company_id.delay_count', default=0)
	done_stage_ckecklist = fields.Many2one('project.task.type',	string='Done Stage', related='company_id.done_stage_ckecklist')
	todo_stage_ckecklist = fields.Many2one('project.task.type',	string='To Do Stage', related='company_id.todo_stage_ckecklist'	)
	cancel_stage_ckecklist = fields.Many2one('project.task.type', string='Cancel Stage', related='company_id.cancel_stage_ckecklist')
	warning_child_task = fields.Many2one('project.task.type', string='Prevent stage to change until all tasks on the same stage', related='company_id.warning_child_task'	)

	first_reminder = fields.Float(string='First Reminder (Days)', related='company_id.first_reminder'	)
	second_reminder = fields.Float(string='Second Reminder (Days)',	related='company_id.second_reminder')
	first_date = fields.Date(string='First Reminder Date', related='company_id.first_date')
	second_date = fields.Date(string='Second Reminder Date', related='company_id.second_date')
	allow_multi_task = fields.Boolean(string='Allow Multi Task', related='company_id.allow_multi_task')


	def validate_date(self):
		if self.first_reminder > self.second_reminder:
			return True
		else:
			raise UserError(_('First Reminder(Days) should be greater than Second Reminder(Days)'))
		return False


	@api.onchange('first_reminder')
	def convert_first_date(self):
		self.first_date = None
		for tasks in self.env['project.task'].search([]):
			if tasks.date_deadline !=False:
				reminder_date = datetime.strptime(tasks.date_deadline.strftime("%Y/%m/%d %H:%M:%S"),"%Y/%m/%d %H:%M:%S")
				first = reminder_date - timedelta(days=self.first_reminder)
				then = datetime.strptime(str(first), '%Y-%m-%d %H:%M:%S').date()
				today = datetime.now().date()
				if then == today:
					self.first_date = then


	@api.onchange('second_reminder')
	def convert_second_date(self):
		self.second_date = None
		for proj_task in self.env['project.task'].search([]):
			if proj_task.date_deadline !=False:
				reminders_date = datetime.strptime(proj_task.date_deadline.strftime("%Y/%m/%d %H:%M:%S"),"%Y/%m/%d %H:%M:%S")
				second = reminders_date - timedelta(days=self.second_reminder)
				now = datetime.strptime(str(second), '%Y-%m-%d %H:%M:%S').date()
				today = datetime.now().date()
				if now == today:
					self.second_date = now
# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError
from datetime import datetime, timedelta,date
from odoo.tools.safe_eval import safe_eval


class ProjectInherit(models.Model):
    _inherit = "project.project"
    _description = "Projects"

    sub_project_ids = fields.One2many('sub.project', 'project_id', string="Sub Projects")
    sub_task_count = fields.Integer(compute="compute_sub_task_count")
    privacy_visibility = fields.Selection([
        ('followers', 'Invited employees'),
        ('employees', 'All employees'),
        ('portal', 'Portal users and all employees'),
    ],
        string='Visibility', required=True,
        default='followers',
        help="Defines the visibility of the tasks of the project:\n"
             "- Invited employees: employees may only see the followed project and tasks.\n"
             "- All employees: employees may see all project and tasks.\n"
             "- Portal users and all employees: employees may see everything."
             "   Portal users may see project and tasks followed by.\n"
             "   them or by someone of their company.")
    task_auto_assign_ids = fields.One2many('task.auto.assign', 'project_id')
    task_sequence_id = fields.Many2one('ir.sequence',string="Task Entry Sequence")
    seq1 = fields.Char("Number")
    seq2 = fields.Char(string="Add Prefix")
    order_id = fields.Many2one('sale.order', string="Sale Order ")
    sale_order_ids = fields.Many2many('sale.order', 'sales_order_project_project_rel', string="Sale Orders")

    def compute_sub_task_count(self):
        for rec in self:
            rec.sub_task_count = len(rec.sub_project_ids)

    def unlink(self):
        for remove in self:
            if len(remove.sub_project_ids) > 0:
                raise UserError(_("Sorry !!! You cannot delete this project, because it has sub project(s)"))
        return super(ProjectInherit, self).unlink()

    @api.model
    def default_get(self, fields):
        res = super(ProjectInherit, self).default_get(fields)
        stages_lines = []
        task_ids = self.env['project.task.type'].search([])
        stages = [x.id for x in task_ids]
        stages_lines += [(0, 0, {'type_ids': stages})]
        project_stage_ids = self.env['project.task.type'].search([('dft_for_new_project', '=', True)])
        stage_list = []
        if project_stage_ids:
            for stage in project_stage_ids:
                values = {}
                values.update({'stage_id': stage.id, 'user_ids': stage.dft_assign_user_id.id})
                stage_list.append((0, 0, values))

        res.update({'task_auto_assign_ids': stage_list})
        return res

    # validation on blank user and stage.
    @api.constrains('task_auto_assign_ids')
    def onchange_auto_assign_ids(self):
        if self.task_auto_assign_ids:
            for each in self.task_auto_assign_ids:
                if not each.user_ids or not each.stage_id:
                    raise ValidationError(_(" Please enter valid Users and Stages.!"))


    # if default new is true then new created project is automatically add.
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            project_obj = self.env['project.project'].search(
                [('task_auto_assign_ids.stage_id.dft_for_new_project', '=', True)])
            plist = []
            for vals in vals_list:
                vals['seq1'] = self.env['ir.sequence'].next_by_code('project.project') or _('New')
            record = super(ProjectInherit, self).create(vals)
            plist.append(record.id)
            for p in project_obj:
                plist.append(p.id)
            stage_obj = self.env['project.task.type'].search([('dft_for_new_project', '=', True)])
            for stage in stage_obj:
                stage.write({'project_ids': [(6, 0, plist)]})
            return record

class SubProject(models.Model):
    _name = 'sub.project'
    _description = "Sub Projects"

    user_id = fields.Many2one('res.users', "Project Manager")
    partner_id = fields.Many2one('res.partner', string='Customer')
    project_id = fields.Many2one('project.project', string='Project', store=True)
    p_project_id = fields.Many2one('project.project', string='Project ', store=True)

    @api.onchange('p_project_id')
    def set_sub_project_vals(self):
        if self.p_project_id:
            self.user_id = self.p_project_id.user_id
            self.partner_id = self.p_project_id.partner_id

    def unlink(self):
        for remove in self:
            if len(remove.p_project_id.task_ids) > 0:
                raise UserError(_("Sorry !!! You cannot delete this project, because it has Task(s)"))
        return super(SubProject, self).unlink()

class CalenderEvent(models.Model):
    _inherit = 'calendar.event'

    task_id = fields.Many2one('project.task', string="Task", readonly=True)
    project_id = fields.Many2one('project.project',string="Project")
    task_count = fields.Integer('Tasks', compute='_compute_task',)

    # count task 
    @api.depends('task_id')
    def _compute_task(self):
        self.task_count = self.env['project.task'].search_count([('meeting_id','=',self.id)])

class MeetingDate(models.TransientModel):
    _name = 'meeting.date'
    _description = "Create Meeting from Task"

    start_date = fields.Datetime('Meeting Date', required=True)
    
    def get_data(self):
        task_obj= self.env['project.task'].browse(self._context.get('active_ids'))
        calendar_obj = self.env['calendar.event'].create({'name':"Meeting from : "+task_obj.name , 'start':str(self.start_date),'duration':1, 'stop':self.start_date + timedelta(hours=1),'task_id':task_obj.id, 'project_id':task_obj.project_id.id})
        task_obj.write({'meeting_id':calendar_obj.id})

class TaskAutoAssign(models.Model):
    _name = "task.auto.assign"
    _description = "Task Auto Assign"

    project_id = fields.Many2one('project.project', string='Project')
    stage_id = fields.Many2one('project.task.type')
    user_ids = fields.Many2one('res.users')

    _sql_constraints = [('project_stage_uniq', 'unique (project_id,stage_id,user_ids)',
                         'Duplicate entry is not allowed !')]

    # add project in stages from project using add stages and user
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            project_obj = self.env['project.project'].search([])
            stage_obj = self.env['project.task.type'].search([])
            get_stage = vals.get('stage_id')
            plist = []
            record = super(TaskAutoAssign, self).create(vals)
            proj_list = []
            for each in project_obj:
                if each.task_auto_assign_ids:
                    proj_list.append(each.id)
            for p in proj_list:
                for stage in stage_obj:
                    if stage.id == get_stage:
                        plist.append(p)
                        stage.write({'project_ids': [(6, 0, plist)]})
            return record


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    @api.depends('project_id', 'task_ids')
    def _total_task_count(self):
        for order in self:

            order.task_count = len(order.task_ids)



    task_count = fields.Integer('Task Count', compute='_total_task_count',)
    project_id = fields.Many2one('project.project', string="Project", readonly=True, copy=False)
    task_ids = fields.One2many('project.task', 'order_id', string="Tasks ", readonly=True, copy=False)
    order_task_created = fields.Boolean(string='Order Task Created', default=False, copy=False)

    def add_task(self):
        action = self.env.ref('bi_all_in_one_project_management_system.action_task_create_create').sudo().read()[0]
        return action

    def action_view_project(self):
        domain = []
        if self.order_task_created:
            domain = [('id','in',self.task_ids.ids)]
        action = self.with_context(active_id=self.project_id.id).env.ref('bi_all_in_one_project_management_system.act_project_project_2_project_task_my').sudo().read()[0]
        if action.get('context'):
            eval_context = self.env['ir.actions.actions']._get_eval_context()
            eval_context.update({'active_id': self.project_id.id,'search_default_my_tasks' : 1})
            action['context'] = safe_eval(action['context'], eval_context)
            action['domain'] = [('is_empty','=',False)] + domain
        return action
    

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    order_project_id = fields.Many2one('project.project', string="Order Related Project")
    
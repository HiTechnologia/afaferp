# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split

class AddATask(models.TransientModel):
    _name = 'sale.task.create'
    _description = 'Add a Task'

    @api.model
    def default_get(self, field_vals):
        res = super(AddATask, self).default_get(field_vals)
        order_id = self.env['sale.order'].browse(self._context.get('active_id'))

        date = fields.Date.context_today(self)

        date_deadline = date + relativedelta(days=1)

        team_id = order_id.team_id

        res.update({
            'order_id' : False,
            'order_true' : False,
            'product_id' : False,
            'team_id' : team_id.id,
            'project_id' : team_id.order_project_id.id,
            'date' : date_deadline,
        })
            
        if self._context.get('active_model') == 'sale.order':
            order_id = self.env['sale.order'].browse(self._context.get('active_id'))

            date = fields.Date.context_today(self)

            date_deadline = date + relativedelta(days=1)

            res.update({
                'order_id' : self._context.get('active_id'),
                'order_true' : True,
                'project_id' : order_id.team_id.order_project_id.id,
                'date' : date_deadline,
                'product_id' : False
            })
        return res

    name = fields.Char(string='Task Title')
    order_true = fields.Boolean(string='Order')
    order_id = fields.Many2one('sale.order', string='Order.')
    product_id = fields.Many2one('product.template', string='Product')
    team_id = fields.Many2one('crm.team',string='Sales Team')
    user_ids = fields.Many2many('res.users', relation='sale_project_task_user_rel', column1='task_id', column2='user_id',
    string='Assignees', default=lambda self: self.env.user)
    project_id = fields.Many2one('project.project', string='Project')
    date = fields.Date('Date Deadline')

    def save_nd_edit(self):
        for task in self:
            task_id = self.env['project.task']
            if task.order_true:
                stage_id = self.env['project.task.type'].search([
                    ('name','=','Awaiting Internal')],limit=1)

                record_id = self.env['project.task'].browse(self._context.get('active_id'))

                task_id = self.env['project.task'].create({
                    'name': task.name or '',
                    'stage_id' : stage_id.id,
                    'project_id': task.project_id.id,
                    'order_id' : task.order_id.id,
                    'user_ids' : task.user_ids.ids,
                    'date_deadline' : task.date,
                    'order_task_created' : True
                }) 

                task.order_id.write({
                    'order_task_created' : True,
                    'task_ids' : [(4,task_id.id)],
                    'project_id' : task.project_id.id
                })

                project_ids = stage_id.mapped('project_ids')
                if task.project_id not in project_ids:
                    stage_id.write({
                        'project_ids' : [(4, task.project_id.id)]
                    })
            else:
                stage_id = self.env['project.task.type'].search([
                    ('name','=','Awaiting Internal')],limit=1)

                record_id = self.env['project.task'].browse(self._context.get('active_id'))

                task_id = self.env['project.task'].create({
                    'name': task.name or '',
                    'stage_id' : stage_id.id,
                    'project_id': task.project_id.id,
                    'order_id' : task.order_id.id,
                    'user_ids' : task.user_ids.ids,
                    'date_deadline' : task.date,
                    'order_task_created' : True
                }) 

                task.order_id.write({
                    'order_task_created' : True,
                    'task_ids' : [(4,task_id.id)],
                    'project_id' : task.project_id.id
                })

                project_ids = stage_id.mapped('project_ids')
                if task.project_id not in project_ids:
                    stage_id.write({
                        'project_ids' : [(4, task.project_id.id)]
                    })

            action = self.with_context(active_id=self.project_id.id).env.ref('bi_all_in_one_project_management_system.act_project_project_2_project_task_my').sudo().read()[0]
            action['views'] = [(self.env.ref('project.view_task_form2').id, 'form')]
            action['context'] = dict(self.env.context)
            action['context']['form_view_initial_mode'] = 'edit'
            action['res_id'] = task_id.id
            return action

    def save_nd_new(self):
        for task in self:   
            task_id = self.env['project.task']
            if task.order_true:
                stage_id = self.env['project.task.type'].search([
                    ('name','=','Awaiting Internal')],limit=1)

                record_id = self.env['project.task'].browse(self._context.get('active_id'))

                task_id = self.env['project.task'].create({
                    'name': task.name or '',
                    'stage_id' : stage_id.id,
                    'project_id': task.project_id.id,
                    'order_id' : task.order_id.id,
                    'user_ids' : task.user_ids.id,
                    'date_deadline' : task.date,
                    'order_task_created' : True
                }) 

                task.order_id.write({
                    'order_task_created' : True,
                    'task_ids' : [(4,task_id.id)],
                    'project_id' : task.project_id.id
                })

                project_ids = stage_id.mapped('project_ids')
                if task.project_id not in project_ids:
                    stage_id.write({
                        'project_ids' : [(4, task.project_id.id)]
                    })
            else:
                stage_id = self.env['project.task.type'].search([
                    ('name','=','Awaiting Internal')],limit=1)

                record_id = self.env['project.task'].browse(self._context.get('active_id'))

                task_id = self.env['project.task'].create({
                    'name': task.name or '',
                    'stage_id' : stage_id.id,
                    'project_id': task.project_id.id,
                    'order_id' : task.order_id.id,
                    'user_ids' : task.user_ids.ids,
                    'date_deadline' : task.date,
                    'order_task_created' : True
                }) 

                task.order_id.write({
                    'order_task_created' : True,
                    'task_ids' : [(4,task_id.id)],
                    'project_id' : task.project_id.id
                })

                project_ids = stage_id.mapped('project_ids')
                if task.project_id not in project_ids:
                    stage_id.write({
                        'project_ids' : [(4, task.project_id.id)]
                    })


            action = self.env.ref('bi_all_in_one_project_management_system.action_task_create_create').sudo().read()[0]
            ctx = self._context.copy()
            action['context'] = ctx
            return action

    def add_a_task(self):
        for task in self:   
            task_id = self.env['project.task']
            if task.order_true:

                stage_id = self.env['project.task.type'].search([
                    ('name','=','Awaiting Internal')],limit=1)

                record_id = self.env['project.task'].browse(self._context.get('active_id'))

                task_id = self.env['project.task'].create({
                    'name': task.name or '',
                    'stage_id' : stage_id.id,
                    'project_id': task.project_id.id,
                    'order_id' : task.order_id.id,
                    'user_ids' : task.user_ids.ids,
                    'date_deadline' : task.date,
                    'order_task_created' : True
                }) 

                task.order_id.write({
                    'order_task_created' : True,
                    'task_ids' : [(4,task_id.id)],
                    'project_id' : task.project_id.id
                })

                project_ids = stage_id.mapped('project_ids')
                if task.project_id not in project_ids:
                    stage_id.write({
                        'project_ids' : [(4, task.project_id.id)]
                    })

            else:
                stage_id = self.env['project.task.type'].search([
                    ('name','=','Awaiting Internal')],limit=1)

                record_id = self.env['project.task'].browse(self._context.get('active_id'))

                task_id = self.env['project.task'].create({
                    'name': task.name or '',
                    'stage_id' : stage_id.id,
                    'project_id': task.project_id.id,
                    'task_product_id' : task.product_id.id,
                    'user_ids' : task.user_ids.ids,
                    'date_deadline' : task.date,
                    
                }) 

                task.product_id.write({
                    'task_ids' : [(4,task_id.id)],
                    'project_id' : task.project_id.id
                })

                project_ids = stage_id.mapped('project_ids')
                if task.project_id not in project_ids:
                    stage_id.write({
                        'project_ids' : [(4, task.project_id.id)]
                    })

            return True
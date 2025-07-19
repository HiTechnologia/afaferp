# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _


class ProjectChecklist(models.Model):
    _name = "project.checklist"
    _description = "Project checklist"

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string="Name")
    description = fields.Char(string="Description")


class ProjectChecklistLine(models.Model):
    _name = "project.checklist.line"
    _description = "Project checklist Line"

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string="Name")
    checklist_id = fields.Many2one('project.checklist', string="name")
    project_id = fields.Many2one("project.project", string="project id")
    description = fields.Char(string="Description")
    date = fields.Date(default=fields.Date.today)
    state = fields.Selection([
        ('new', 'New'),
        ('complete', 'Complete'),
        ('cancel', 'Cancel')], string='State',
        copy=False, default="new")

    @api.onchange('checklist_id')
    def _onchange_checklist_id(self):
        for checklist in self:
            description = ''
            if checklist.checklist_id:
                description = checklist.checklist_id.description
            checklist.update({
                'description' : description
            })


    

    def action_complete(self):
        for rec in self:
            rec.state = 'complete'
            checklist_len = len(rec.project_id.checklist_line_ids)
            completed_progress = len(rec.project_id.checklist_line_ids.filtered(lambda x : x.state == 'complete'))
            
            rec.project_id.write({
                'checklist_progress' : (completed_progress * 100) / (checklist_len or 1)
            })


    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            checklist_len = len(rec.project_id.checklist_line_ids)
            completed_progress = len(rec.project_id.checklist_line_ids.filtered(lambda x : x.state == 'complete'))
            
            rec.project_id.write({
                'checklist_progress' : (completed_progress * 100) / (checklist_len or 1)
            })


    def unlink(self):
        for rec in self:
            project = rec.project_id
            project.checklist_line_ids -= rec 
            checklist_len = len(project.checklist_line_ids)
            completed_progress = len(project.checklist_line_ids.filtered(lambda x: x.state == 'complete'))
            project.write({
                'checklist_progress': (completed_progress * 100) / max((checklist_len or 1), 1)
            })
        return super(ProjectChecklistLine, self).unlink()



class ProjectChecklistTemplate(models.Model):
    _name = "project.checklist.template"
    _description = "Project Checklist Template"
    _rec_name = "template_name"

    sequence = fields.Integer(string="Sequence")
    template_name = fields.Char(string="Name")
    checklist_ids = fields.Many2many('project.checklist', string="Checklist Template")


class ProjectProject(models.Model):
    _inherit = "project.project"

    checklist_progress = fields.Integer(string='Checklist Progress', store=True, default=0.0)
    checklist_template = fields.Many2many('project.checklist.template', string='Project Checklist template')
    checklist_line_ids = fields.One2many('project.checklist.line', 'project_id', string='Checklist')

    @api.onchange('checklist_template')
    def onchange_checklist_template(self):

        if self.checklist_template:
            checklist = []
            for i in self.checklist_template:
                for j in i.checklist_ids:
                    checklist.append((0,0,{
                            'checklist_id' : j._origin.id,
                            'description' : j.description,
                            'project_id' : self.id, 
                    }))
                    self.update({'checklist_line_ids':False})
                self.update({"checklist_line_ids" : checklist})
            

    @api.constrains('checklist_template')
    def _check_checklist_templated(self):
        if not self.checklist_template:
            for lines in self.checklist_line_ids:
                lines.unlink()

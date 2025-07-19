# -- coding: utf-8 --
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HiTech AFAFERP All In One Project Management System - All in one PMS',
    'version': '18.0',
    'category': 'Project',
    'summary': 'Sub Project Access control project delegation project subtask timer project multi assignee daily task update mass stage update project stage project task priority task overdue email project checklist project priority task send by email import task history ',
    'description': """ 

        This odoo app helps user to manage project for all need. User can create subtask for a task, User can start, pause and stop task timer, get automatic email notification on daily and weekly task updates, attach and manage documents for project and task, set priority, mass update task, assign task to multiple users, print project and task PDF report, get email notification on before due date and after due date, manage different stages project dynamically, create meeting from task and view, set user to automatically assign on specific stage, add sequence for project and task, also get email notification on task timesheet limit remainder, create task from sale order, and import task from xls or csv file.


    """,
    'author': 'HiTechnologia',
    'depends': ['base', 'project', 'calendar', 'sale_management', 'hr_timesheet'],
    'data': [
        'security/sub_project_security.xml',
        'security/ir.model.access.csv',
        'security/multi_user_assign_security.xml',
        'views/project_task_view.xml',
        'views/sub_project_view.xml',
        'views/project_view.xml',
        'data/data_view.xml',
        'data/task_template_view.xml',
        'data/remider_alert_mail_data.xml',
        'data/remider_alert_cron.xml',
        'views/ir_attachment.xml',
        'views/view_task_form.xml',
        'data/mail_data.xml',
        'wizard/mass_update_task_wiz.xml',
        'report/project_task_report.xml',
        'report/task_details_view.xml',
        'report/project_details_view.xml',
        'views/res_settings_views.xml',
        'wizard/create_task_view.xml',
        'wizard/update_project_stage_view.xml',
        'views/task.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'bi_all_in_one_project_management_system/static/src/js/**/*',
            'bi_all_in_one_project_management_system/static/src/xml/timer_view.xml',
        ],
    },

    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    "images": ['static/description/Banner.gif'],
    'license': 'OPL-1',
}

from odoo import fields, models


class ProcurementSchedulerLog(models.Model):
    _name = 'procurement.scheduler.log'
    _description = 'Logs of the Procurement Scheduler'
    _order = 'create_date desc'

    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True)
    start_datetime = fields.Datetime(string='Start Date', readonly=True)

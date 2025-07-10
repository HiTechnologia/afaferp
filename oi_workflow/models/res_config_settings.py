
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    module_oi_workflow_expense = fields.Boolean(string='Employee Expenses')
    module_oi_workflow_hr_contract = fields.Boolean(string='Employee Contracts')
    module_oi_workflow_hr_holidays = fields.Boolean(string='Employee Time Off')
    module_oi_workflow_hr_holidays_manager = fields.Boolean(string='Employee Time Off / Employee Manager')
    module_oi_workflow_hr_payslip_run = fields.Boolean(string='Payslip Batches (Community)')
    module_oi_workflow_hr_payslip_run_e = fields.Boolean(string='Payslip Batches (Enterprise)')
    module_oi_workflow_purchase_order = fields.Boolean(string='Purchase Order')
    module_oi_workflow_purchase_requisition = fields.Boolean(string="Purchase Requisition")
    module_oi_workflow_sale_order = fields.Boolean(string='Sale Order')
    module_oi_workflow_account_payment = fields.Boolean(string='Account Payment')
    module_oi_workflow_crm_lead = fields.Boolean(string='CRM Lead')
    module_oi_workflow_invoice = fields.Boolean(string='Invoice')
    module_oi_workflow_project = fields.Boolean(string='Project')
    module_oi_workflow_project_task = fields.Boolean(string='Project Task')
    
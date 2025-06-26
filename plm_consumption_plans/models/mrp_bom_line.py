
from odoo import models, fields


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    template_consumption_plan_ids = fields.Many2many(
        comodel_name="template.consumption.plan",
        string="Consumption Plans",
        compute="_compute_template_consumption_plan_ids",
        readonly=True
    )

    def _compute_template_consumption_plan_ids(self):
        for bom_line in self:
            plans = self.env['template.consumption.plan'].search([('product_ids', 'in', bom_line.product_id.id)])
            bom_line.template_consumption_plan_ids = plans

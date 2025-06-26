from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    template_consumption_plan_ids = fields.Many2many(
        comodel_name="template.consumption.plan",
        string="Consumption Plans",
        compute="_compute_template_consumption_plan_ids",
        readonly=True
    )

    def _compute_template_consumption_plan_ids(self):
        for product_template in self:
            plans = self.env['template.consumption.plan'].search([('product_template_ids', 'in', product_template.id)])
            product_template.template_consumption_plan_ids = plans

    def act_get_consumption_plan_report(self):
        self.ensure_one()
        return self.env.ref('plm_consumption_plans.report_action_consumption_plan').report_action(self)

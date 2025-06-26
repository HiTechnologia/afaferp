from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    template_consumption_plan_ids = fields.Many2many(
        comodel_name="template.consumption.plan",
        string="Consumption Plans",
        compute="_compute_template_consumption_plan_ids",
        readonly=True
    )

    def _compute_template_consumption_plan_ids(self):
        for product in self:
            plans = self.env['template.consumption.plan'].search([('product_ids', 'in', product.id)])
            product.template_consumption_plan_ids = plans

    def act_get_consumption_plan_report(self):
        self.ensure_one()
        return self.env.ref('plm_consumption_plans.report_action_consumption_plan_product_variant').report_action(self)

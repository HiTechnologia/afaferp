from odoo import models, fields


class TemplateConsumptionPlan(models.Model):
    _name = "template.consumption.plan"
    _description = "Template Comsumption Plan"
    _rec_name = 'name'

    name = fields.Char(string="Name")
    time_span = fields.Float(string="Hours")
    consumption_state_id = fields.Many2one(string="Consumption_state_id", comodel_name="consumption.state")
    product_template_ids = fields.Many2many(
        comodel_name="product.template", string="Product Templates"
    )
    product_ids = fields.Many2many(comodel_name="product.product", string="Products")

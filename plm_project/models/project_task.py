from odoo import _, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    activity_product_ids = fields.One2many(
        "product.product", "activity_task_id", string=_("Product Ids")
    )

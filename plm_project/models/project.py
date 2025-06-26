from odoo import _, api, fields, models


class ProjectExtension(models.Model):
    _inherit = "project.project"

    def _compute_plm_complete(self):
        """
        compute the percentage of the product completed
        """
        for project in self:
            if project.plm_product_ids:
                product_ok = 0
                for product in project.plm_product_ids:
                    if product.engineering_state in ["released"]:
                        product_ok = product_ok + 1
                project.plm_completed = round(
                    100.0 * product_ok / len(project.plm_product_ids), 2
                )
            else:
                project.plm_completed = 100

    def _compute_product_count(self):
        for project in self:
            project.plm_product_count = len(project.plm_product_ids)

    plm_use_plm = fields.Boolean(
        string="Use PLM",
        default=False,
        help=_("Check this box to manage plm data into project"),
        compute="_compute_plm_use_plm",
        store=True
    )
    plm_completed = fields.Float(
        string=_("Plm Complete"), compute="_compute_plm_complete"
    )
    plm_product_ids = fields.Many2many(
        "product.product",
        "project_product_rel",
        "project_id",
        "product_id",
        string=_("Products"),
    )
    plm_product_count = fields.Integer(
        compute="_compute_product_count", string=_("Number of product related")
    )

    total_components = fields.Integer(string="Total Components", compute="_compute_component_stats")
    released_components = fields.Integer(string="Released Components", compute="_compute_component_stats")

    @api.depends('plm_product_ids')
    def _compute_plm_use_plm(self):
        for rec in self:
            if rec.plm_product_ids:
                rec.plm_use_plm = True
            else:
                rec.plm_use_plm = False


    def action_get_product_variant_list_view(self):
        self.ensure_one()
        list_view_id = self.env.ref('plm_project.view_product_product_list_plm_colored').id
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'views': [(list_view_id, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.plm_product_ids.ids)],
            'context': {
                'create': False,
                'group_by': 'engineering_state',
            },
            'target': 'current',
        }

    @api.depends('plm_product_ids')  # Update this field name to actual relation
    def _compute_component_stats(self):
        for project in self:
            components = project.plm_product_ids
            project.total_components = len(components)
            project.released_components = len(components.filtered(lambda x: x.engineering_state == 'released'))
